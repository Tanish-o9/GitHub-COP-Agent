"""
Autonomous Engineering REST API Routes
Provides task intake, planning, human approval, feedback processing, and timeline endpoints under /api/v1/engineering/.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, EngineeringTaskModel, TaskCriterionModel, AuditLog
from api.auth import get_current_user
from autonomous_engine import AutonomousEngineeringController
from feedback_engine import FeedbackEngine
from checkpoint_manager import CheckpointManager
from mcp_lifecycle import MCPConnectionPool

router = APIRouter(prefix="/api/v1/engineering", tags=["Autonomous Engineering"])


class TaskIntakeRequest(BaseModel):
    repository_name: str
    objective: str
    task_type: str = "REPO_INTELLIGENCE"
    autonomy_level: int = 2
    explicit_criteria: Optional[List[str]] = None


class FeedbackRequest(BaseModel):
    event_type: str = "CI_FAILURE"
    raw_content: str


@router.post("/tasks")
def intake_engineering_task(
    req: TaskIntakeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Intake new engineering task, validate contract, and extract criteria."""
    controller = AutonomousEngineeringController(db)
    result = controller.intake_task(
        tenant_id=current_user.id,
        repository_name=req.repository_name,
        objective=req.objective,
        task_type=req.task_type,
        autonomy_level=req.autonomy_level,
        explicit_criteria=req.explicit_criteria
    )
    return result


@router.get("/tasks/{task_id}")
def get_task_details(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch details and criteria for an engineering task."""
    task = db.query(EngineeringTaskModel).filter(EngineeringTaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found.")
    
    # Enforce tenant isolation
    if task.tenant_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    criteria = db.query(TaskCriterionModel).filter(TaskCriterionModel.task_id == task_id).all()
    return {
        "id": task.id,
        "repository_name": task.repository_name,
        "objective": task.objective,
        "status": task.status,
        "autonomy_level": task.autonomy_level,
        "created_at": task.created_at,
        "criteria": [
            {
                "id": f"AC-{c.id}",
                "description": c.description,
                "status": c.status,
                "evidence": c.evidence_json.get("evidence", "")
            }
            for c in criteria
        ]
    }


@router.post("/tasks/{task_id}/execute")
def execute_task_pipeline(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute bounded task pipeline through planning and approval gating."""
    task = db.query(EngineeringTaskModel).filter(EngineeringTaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found.")
    
    if task.tenant_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    mcp_tools = MCPConnectionPool.get_connection()
    controller = AutonomousEngineeringController(db)
    return controller.execute_bounded_workflow(task_id, mcp_tools)


@router.post("/tasks/{task_id}/feedback")
def submit_task_feedback(
    task_id: str,
    req: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit CI or PR review feedback for a task."""
    task = db.query(EngineeringTaskModel).filter(EngineeringTaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found.")

    fb_engine = FeedbackEngine()
    item = fb_engine.process_feedback(task_id, {"event_type": req.event_type, "text": req.raw_content})
    return item.to_dict()


@router.get("/tasks/{task_id}/timeline")
def get_task_timeline(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch chronological step checkpoints and timeline for a task."""
    chk_mgr = CheckpointManager(db)
    checkpoints = chk_mgr.get_all_checkpoints(task_id)
    return {
        "task_id": task_id,
        "timeline": [
            {
                "step": c.step_name,
                "status": c.status,
                "timestamp": c.created_at,
                "state": c.state_json
            }
            for c in checkpoints
        ]
    }
