import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from loguru import logger
from crew import run

# ── Logging ───────────────────────────────────────────────────────────────────
logger.remove()  # drop default handler so we control format
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
)
logger.add(
    "logs/scheduler.log",
    rotation="1 week",
    retention="4 weeks",
    level="DEBUG",
    encoding="utf-8",
)


# ── Job ───────────────────────────────────────────────────────────────────────
def run_digest():
    logger.info("Digest run starting")
    try:
        run()
        logger.info("Digest run completed successfully")
    except Exception as exc:
        logger.exception(f"Digest run failed: {exc}")


def on_job_event(event):
    if event.exception:
        logger.error(f"Job {event.job_id} crashed — see above for traceback")
    else:
        logger.info(f"Job {event.job_id} finished cleanly")


# ── Scheduler ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="America/New_York")
    scheduler.add_listener(on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    # TEST: fire every 2 minutes
    scheduler.add_job(run_digest, "interval", minutes=2, id="digest")

    # PRODUCTION: every morning at 8am ET (swap in when ready)
    # scheduler.add_job(run_digest, "cron", hour=8, minute=0, id="digest")

    logger.info("Scheduler started — press Ctrl+C to stop")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler shutting down")
        scheduler.shutdown(wait=False)
