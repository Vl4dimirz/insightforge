"""
Automation endpoints — inspect and trigger the background scheduler.

  • GET  /automation/status  → is it running, how often, last run, scheduled jobs
  • POST /automation/run-now → fire the job immediately
"""

from fastapi import APIRouter

from app import automation

router = APIRouter(prefix="/automation", tags=["Automation"])


@router.get("/status")
def automation_status() -> dict:
    return automation.status()


@router.post("/run-now")
def automation_run_now() -> dict:
    return automation.run_now()
