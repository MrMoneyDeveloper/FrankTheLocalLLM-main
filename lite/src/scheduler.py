import time
from apscheduler.schedulers.background import BackgroundScheduler

_scheduler = BackgroundScheduler()


def nightly_job():
    # placeholder for maintenance jobs (summaries, cleanup)
    pass


def start_scheduler():
    _scheduler.add_job(nightly_job, "cron", hour=3, minute=0)
    _scheduler.start()


if __name__ == "__main__":
    start_scheduler()
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        _scheduler.shutdown()

