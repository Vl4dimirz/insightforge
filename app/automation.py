"""
The automation layer — a background scheduler that runs jobs on an interval.

This is the "automation" half of the platform: APScheduler keeps running inside
the API process and fires jobs on a schedule (no cron, no extra service). The
demo job here is a lightweight heartbeat; a real job (re-scrape a URL, rebuild a
report, email a summary) plugs in exactly the same way via _scheduler.add_job().
"""

from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

_scheduler = BackgroundScheduler(daemon=True)
_state = {"started": False, "runs": 0, "last_run": None}

HEARTBEAT_SECONDS = 30


def _heartbeat() -> None:
    _state["runs"] += 1
    _state["last_run"] = datetime.now(timezone.utc).isoformat()


def start_scheduler() -> None:
    if _state["started"]:
        return
    _scheduler.add_job(_heartbeat, "interval", seconds=HEARTBEAT_SECONDS, id="heartbeat",
                       next_run_time=datetime.now(timezone.utc))
    _scheduler.start()
    _state["started"] = True


def stop_scheduler() -> None:
    if _state["started"]:
        _scheduler.shutdown(wait=False)
        _state["started"] = False


def run_now() -> dict:
    """Trigger the job immediately (handy for testing / manual runs)."""
    _heartbeat()
    return status()


def status() -> dict:
    jobs = [
        {"id": j.id, "next_run": j.next_run_time.isoformat() if j.next_run_time else None}
        for j in _scheduler.get_jobs()
    ]
    return {
        "running": _state["started"],
        "interval_seconds": HEARTBEAT_SECONDS,
        "total_runs": _state["runs"],
        "last_run": _state["last_run"],
        "jobs": jobs,
    }
