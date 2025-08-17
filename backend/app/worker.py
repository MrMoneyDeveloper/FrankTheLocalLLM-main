from __future__ import annotations

import json
from pathlib import Path

from celery import Celery
from langchain_community.llms import Ollama

from .db import SessionLocal
from .models import User

celery_app = Celery("worker", broker="redis://localhost:6379/0")

_STATE_FILE = Path(__file__).resolve().parents[1] / "data" / "summary_state.json"
_SUMMARY_FILE = Path(__file__).resolve().parents[1] / "data" / "user_summaries.json"


def _read_json(path: Path) -> dict | list | int | str:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:  # pragma: no cover - corrupted file
            return {}
    return {}


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data))


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(60.0, summarize_new_users.s())


@celery_app.task
def summarize_new_users():
    state = _read_json(_STATE_FILE)
    last_id = state.get("last_id", 0)
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.id > last_id).order_by(User.id).all()
    finally:
        db.close()
    if not users:
        return "No new users"

    llm = Ollama(model="llama3")
    content = "\n".join(u.username for u in users)
    summary = llm.invoke(f"Summarize the following new users:\n{content}")

    summaries = _read_json(_SUMMARY_FILE) or []
    summaries.append({"users": [u.id for u in users], "summary": summary})
    _write_json(_SUMMARY_FILE, summaries)
    _write_json(_STATE_FILE, {"last_id": users[-1].id})
    return summary
