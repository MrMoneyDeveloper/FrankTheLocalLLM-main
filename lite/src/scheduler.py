import time
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler

_scheduler = BackgroundScheduler(timezone="UTC")


def nightly_job():
    # placeholder for maintenance jobs (summaries, cleanup)
    pass


def _do_reindex(note_id: str):
    try:
        from .storage.config import load_settings
        from .storage.indexing import reindex_note
        from .storage import notes as notes_store

        s = load_settings()
        rec = notes_store.get_note(note_id)
        reindex_note(note_id, rec.get("title", ""), rec.get("content", ""), s["CHUNK_SIZE"], s["CHUNK_OVERLAP"])
    except Exception:
        pass


def schedule_reindex(note_id: str, immediate: bool = False):
    delay_ms = 0
    try:
        from .storage.config import load_settings

        s = load_settings()
        delay_ms = int(s.get("REINDEX_DEBOUNCE_MS", 500))
    except Exception:
        delay_ms = 500
    run_at = datetime.now(timezone.utc) + timedelta(milliseconds=(0 if immediate else delay_ms))
    _scheduler.add_job(_do_reindex, id=f"reindex:{note_id}", args=[note_id], run_date=run_at, replace_existing=True)


def start_scheduler():
    # nightly maintenance
    try:
        _scheduler.add_job(nightly_job, "cron", hour=3, minute=0)
    except Exception:
        pass
    _scheduler.start()


if __name__ == "__main__":
    start_scheduler()
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        _scheduler.shutdown()
