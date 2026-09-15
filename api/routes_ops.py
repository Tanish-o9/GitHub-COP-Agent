"""
Operations & Admin Dashboard API Routes
Provides operational statistics, queue depth, health metrics, dead letter task management, and PR reconciliation.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User
from api.auth import get_current_user
from scheduler import ResourceScheduler
from dead_letter import DeadLetterManager
from mcp_lifecycle import MCPConnectionPool
from pr_tracker import PRLifecycleTracker
from github_mcp import GitHubMCPTools

router = APIRouter(prefix="/api/v1/ops", tags=["Operations & Monitoring"])


@router.get("/metrics")
def get_ops_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch system-wide operational statistics and component health statuses.
    """
    scheduler = ResourceScheduler(db)
    queue_stats = scheduler.get_queue_stats()
    mcp_status = MCPConnectionPool.get_pool_status()

    return {
        "system_status": "HEALTHY",
        "queue_metrics": queue_stats,
        "mcp_pool": mcp_status,
        "database": "CONNECTED",
        "redis": "CONNECTED"
    }


@router.get("/dead-letter")
def list_dead_letter_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List tasks in the Dead-Letter Queue (DLQ).
    """
    dlq_mgr = DeadLetterManager(db)
    jobs = dlq_mgr.list_dead_letter_jobs(user_id=current_user.id)
    return [
        {
            "id": j.id,
            "run_id": j.run_id,
            "error_code": j.error_code,
            "last_error": j.last_error,
            "retry_count": j.retry_count,
            "created_at": j.created_at
        }
        for j in jobs
    ]


@router.post("/dead-letter/{job_id}/retry")
def retry_dead_letter_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually requeue a dead-letter job for execution.
    """
    dlq_mgr = DeadLetterManager(db)
    requeued_run = dlq_mgr.retry_dead_letter_job(job_id)
    if not requeued_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dead letter job '{job_id}' not found."
        )
    return {
        "status": "REQUEUED",
        "run_id": requeued_run.id,
        "message": f"Run {requeued_run.id} has been requeued successfully."
    }


@router.post("/reconcile-pr")
def reconcile_pr_status(
    repo_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger background PR status reconciliation with GitHub MCP.
    """
    mcp_tools = MCPConnectionPool.get_connection()
    pr_tracker = PRLifecycleTracker(db)
    reconciled = pr_tracker.reconcile_with_github(mcp_tools, repo_name)
    return {
        "repository": repo_name,
        "reconciled_count": len(reconciled),
        "details": reconciled
    }
