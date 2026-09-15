"""
Agent Runs API Endpoints (/api/v1/runs)
Manages asynchronous agent workflow execution, status monitoring, and cancellation.
"""
import uuid
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, Repository, AgentRun, AgentStep, AuditLog
from api.auth import get_current_user
from worker.task_queue import TaskQueue
from worker.worker_main import execute_agent_run_task

router = APIRouter(prefix="/api/v1/runs", tags=["Agent Runs"])


class RunCreateSchema(BaseModel):
    repository_id: Optional[int] = None
    repo_name: str = "Tanish-o9/GitHub-COP-Agent"
    branch: str = "main"
    user_request: str
    github_token: Optional[str] = None


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_agent_run(
    payload: RunCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enqueue a new long-running multi-agent workflow execution."""
    run_id = f"RUN-{uuid.uuid4().hex[:6].upper()}"

    agent_run = AgentRun(
        id=run_id,
        user_id=current_user.id,
        repository_id=payload.repository_id,
        user_request=payload.user_request,
        status="QUEUED",
        branch_name=payload.branch
    )
    db.add(agent_run)
    db.commit()

    db.add(AuditLog(user_id=current_user.id, action="ENQUEUE_RUN", resource=run_id))
    db.commit()

    # Dispatch to background task worker
    TaskQueue.enqueue_run(
        run_id,
        execute_agent_run_task,
        run_id=run_id,
        repo_name=payload.repo_name,
        user_prompt=payload.user_request,
        branch=payload.branch,
        github_token=payload.github_token
    )

    return {
        "run_id": run_id,
        "status": "QUEUED",
        "message": "Workflow enqueued successfully. Monitor real-time status via WebSocket or GET /api/v1/runs/{id}."
    }


@router.get("")
def list_agent_runs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all agent runs owned by the active user (tenant isolated)."""
    return db.query(AgentRun).filter(AgentRun.user_id == current_user.id).order_by(AgentRun.created_at.desc()).all()


@router.get("/{run_id}")
def get_agent_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get status and step telemetry for a specific agent run."""
    run_record = db.query(AgentRun).filter(
        AgentRun.id == run_id,
        AgentRun.user_id == current_user.id
    ).first()
    if not run_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")

    steps = db.query(AgentStep).filter(AgentStep.run_id == run_id).all()
    return {
        "run_id": run_record.id,
        "status": run_record.status,
        "workflow_type": run_record.workflow_type,
        "user_request": run_record.user_request,
        "branch_name": run_record.branch_name,
        "duration_sec": run_record.duration_sec,
        "created_at": run_record.created_at,
        "steps": steps
    }


@router.post("/{run_id}/cancel")
def cancel_agent_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel an active agent run."""
    run_record = db.query(AgentRun).filter(
        AgentRun.id == run_id,
        AgentRun.user_id == current_user.id
    ).first()
    if not run_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")

    if run_record.status in ["COMPLETED", "FAILED", "CANCELLED"]:
        return {"run_id": run_id, "status": run_record.status, "message": "Run is already finalized"}

    run_record.status = "CANCELLED"
    run_record.updated_at = time.time()
    db.commit()

    db.add(AuditLog(user_id=current_user.id, action="CANCEL_RUN", resource=run_id))
    db.commit()

    return {"run_id": run_id, "status": "CANCELLED", "message": "Agent run successfully cancelled"}
