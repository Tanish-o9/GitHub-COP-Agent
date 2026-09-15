"""
Approvals API Endpoints (/api/v1/approvals)
Manages Human Approval checkpoints and executes approved Git mutations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, Approval, AgentRun, AuditLog
from api.auth import get_current_user
from human_approval import HumanApprovalRequest, ApprovalStatus
from workflows.engineering_workflow import execute_approved_engineering_fix_stateful
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer

router = APIRouter(prefix="/api/v1/approvals", tags=["Human Approvals"])


@router.get("/{approval_id}")
def get_approval(
    approval_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get approval details (enforces tenant ownership)."""
    app_rec = db.query(Approval).filter(
        Approval.id == approval_id,
        Approval.user_id == current_user.id
    ).first()
    if not app_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")
    return app_rec


@router.post("/{approval_id}/approve")
def approve_action(
    approval_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve write operation and execute Git mutations on safe branch."""
    app_rec = db.query(Approval).filter(
        Approval.id == approval_id,
        Approval.user_id == current_user.id
    ).first()
    if not app_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")

    if app_rec.status != "PENDING":
        return {"approval_id": approval_id, "status": app_rec.status, "message": "Approval request already processed"}

    app_rec.status = "APPROVED"
    db.commit()

    # Update AgentRun status
    run_record = db.query(AgentRun).filter(AgentRun.id == app_rec.run_id).first()
    if run_record:
        run_record.status = "PR_CREATED"
        db.commit()

    # Reconstruct HumanApprovalRequest
    req = HumanApprovalRequest(
        action_type=app_rec.action_type,
        repo_name=app_rec.repo_name,
        target_branch=app_rec.target_branch,
        files_to_change=app_rec.payload_json.get("files_to_change", [app_rec.payload_json.get("target_path")]),
        change_summary=app_rec.change_summary,
        generated_tests=[],
        potential_risks=[],
        patch_payload=app_rec.payload_json
    )
    req.approve()

    # Execute mutations
    mcp_tools = GitHubMCPTools()
    tracer = AgentTracer("Execute Approved PR")
    result_msg = execute_approved_engineering_fix_stateful(req, mcp_tools, tracer)

    db.add(AuditLog(user_id=current_user.id, action="APPROVE_ACTION", resource=approval_id))
    db.commit()

    return {"approval_id": approval_id, "status": "APPROVED", "result": result_msg}


@router.post("/{approval_id}/reject")
def reject_action(
    approval_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject proposed write operation."""
    app_rec = db.query(Approval).filter(
        Approval.id == approval_id,
        Approval.user_id == current_user.id
    ).first()
    if not app_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")

    app_rec.status = "REJECTED"
    db.commit()

    run_record = db.query(AgentRun).filter(AgentRun.id == app_rec.run_id).first()
    if run_record:
        run_record.status = "CANCELLED"
        db.commit()

    db.add(AuditLog(user_id=current_user.id, action="REJECT_ACTION", resource=approval_id))
    db.commit()

    return {"approval_id": approval_id, "status": "REJECTED", "message": "Write operation cancelled by user"}
