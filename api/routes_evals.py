"""
Evaluations API Endpoints (/api/v1/evaluations)
Executes Golden Dataset benchmark runs and retrieves evaluation reports.
"""
import uuid
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, EvaluationRun, EvaluationResult, AuditLog
from api.auth import get_current_user
from eval.eval_runner import EvaluationRunner
from report_generator import ReportGenerator

router = APIRouter(prefix="/api/v1/evaluations", tags=["Evaluations"])


@router.post("/run")
def trigger_evaluation_run(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger Golden Dataset Benchmark Evaluation."""
    eval_id = f"EVAL-{uuid.uuid4().hex[:6].upper()}"

    eval_runner = EvaluationRunner()
    metrics = eval_runner.run_benchmark()

    eval_record = EvaluationRun(
        id=eval_id,
        user_id=current_user.id,
        pass_rate_pct=metrics["overall_pass_rate_pct"],
        routing_accuracy_pct=metrics["routing_accuracy_pct"],
        avg_latency_sec=metrics["avg_latency_sec"]
    )
    db.add(eval_record)
    db.commit()

    for res in metrics.get("test_results", []):
        db.add(EvaluationResult(
            eval_run_id=eval_id,
            test_id=res["id"],
            task_type=res["task_type"],
            passed=res["routing_passed"],
            latency_sec=res["latency_sec"]
        ))

    db.add(AuditLog(user_id=current_user.id, action="RUN_EVALUATION", resource=eval_id))
    db.commit()

    reporter = ReportGenerator()
    rep_info = reporter.generate_report(metrics)

    return {
        "eval_id": eval_id,
        "metrics": metrics,
        "report_paths": rep_info
    }


@router.get("")
def list_evaluations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all evaluation runs owned by the active user."""
    return db.query(EvaluationRun).filter(EvaluationRun.user_id == current_user.id).order_by(EvaluationRun.created_at.desc()).all()


@router.get("/{eval_id}")
def get_evaluation(
    eval_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed evaluation run results."""
    eval_rec = db.query(EvaluationRun).filter(
        EvaluationRun.id == eval_id,
        EvaluationRun.user_id == current_user.id
    ).first()
    if not eval_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation run not found")

    results = db.query(EvaluationResult).filter(EvaluationResult.eval_run_id == eval_id).all()
    return {
        "eval_id": eval_rec.id,
        "pass_rate_pct": eval_rec.pass_rate_pct,
        "routing_accuracy_pct": eval_rec.routing_accuracy_pct,
        "avg_latency_sec": eval_rec.avg_latency_sec,
        "created_at": eval_rec.created_at,
        "results": results
    }
