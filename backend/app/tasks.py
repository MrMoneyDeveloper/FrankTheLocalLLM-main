import os
import datetime
from celery import Celery
from celery.schedules import crontab

from .config import Settings
from .db import SessionLocal
from pathlib import Path

from . import models
from .llm import OllamaLLM
from .services.summarization_service import SummarizationService
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

settings = Settings()

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery("backend", broker=BROKER_URL, backend=RESULT_BACKEND)
# Enable eager mode when requested to avoid needing Redis/worker in local dev
if os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() in {"1", "true", "yes"}:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
celery_app.conf.beat_schedule = {
    "summarize-entries": {
        "task": "app.tasks.summarize_entries",
        "schedule": 60.0,
    },
    "daily-digest": {
        "task": "app.tasks.daily_digest",
        "schedule": crontab(hour=0, minute=0),
    },
}

_summarization_service: SummarizationService | None = None


def _get_summarization_service() -> SummarizationService:
    global _summarization_service
    if _summarization_service is None:
        _summarization_service = SummarizationService(OllamaLLM(settings.model))
    return _summarization_service

@celery_app.task
def summarize_entries():
    db = SessionLocal()
    try:
        _get_summarization_service().summarize_pending_entries(db)
        db.commit()
    finally:
        db.close()

@celery_app.task
def embed_chunk(chunk_id: int):
    db = SessionLocal()
    try:
        chunk = db.query(models.Chunk).get(chunk_id)
        if chunk is None:
            return
        embeddings = OllamaEmbeddings(model=settings.embed_model)

        persist_dir = Path(__file__).resolve().parents[1] / "data" / "chroma"
        vectorstore = Chroma(
            embedding_function=embeddings,
            persist_directory=str(persist_dir),
        )
        metadata = {
            "chunk_id": chunk.id,
            "source_path": chunk.file.path if chunk.file else "",
            "line": chunk.start_line,
        }
        vectorstore.add_texts([chunk.content], metadatas=[metadata], ids=[str(chunk.id)])
        vectorstore.persist()

    finally:
        db.close()

def _extract_links(text: str) -> list[str]:
    import re
    return re.findall(r"\[\[(.+?)\]\]", text)

@celery_app.task
def daily_digest():
    db = SessionLocal()
    try:
        since = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        chunks = db.query(models.Chunk).filter(models.Chunk.updated_at >= since).all()
        if not chunks:
            return
        combined = "\n".join(c.content for c in chunks)
        service = _get_summarization_service()
        summary = service.llm_invoke(f"Summarize in <=200 words:\n{combined}")
        tokens = len(summary.split())
        db.add(models.DailySummary(summary=summary.strip(), token_count=tokens))
        db.commit()
        _update_backlinks(db, chunks)
    finally:
        db.close()

def _update_backlinks(db, chunks):
    for chunk in chunks:
        links = _extract_links(chunk.content)
        for title in links:
            target = db.query(models.Chunk).filter(models.Chunk.content.like(f"%# {title}%")).first()
            if target:
                db.add(models.Backlink(source_id=chunk.id, target_id=target.id))
    db.commit()
