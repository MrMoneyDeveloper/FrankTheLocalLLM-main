from celery import Celery
from celery.schedules import crontab
import datetime

from .config import Settings
from .db import SessionLocal
from .llm import OllamaLLM
from .services.summarization_service import SummarizationService
from . import models
from langchain_community.embeddings import OllamaEmbeddings

settings = Settings()

celery_app = Celery("worker", broker=settings.redis_url)
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


summarization_service = SummarizationService(OllamaLLM())


@celery_app.task
def summarize_entries():
    db = SessionLocal()
    try:
        summarization_service.summarize_pending_entries(db)
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
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vector = embeddings.embed_query(chunk.content)
        emb = models.Embedding(chunk_id=chunk.id, vector=vector)
        db.add(emb)
        db.commit()
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
        summary = summarization_service.llm_invoke(f"Summarize in <=200 words:\n{combined}")
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
