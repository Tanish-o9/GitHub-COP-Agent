"""
Dead Letter Manager
Handles dead-letter task storage, inspection, and manual job replay.
"""
import uuid
import time
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from database.models import DeadLetterJob, AgentRun

logger = logging.getLogger(__name__)


class DeadLetterManager:
    """Manages tasks that repeatedly failed and were moved to the Dead-Letter Queue."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def moveToDeadLetter(
        self,
        run_id: str,
        user_id: int,
        error_code: str,
        last_error: str,
        retry_count: int,
        payload: Dict[str, Any]
    ) -> DeadLetterJob:
        """Store failed task into dead letter table and update AgentRun status to DEAD_LETTER."""
        job_id = f"DLQ-{uuid.uuid4().hex[:8].upper()}"
        dead_letter_job = DeadLetterJob(
            id=job_id,
            run_id=run_id,
            user_id=user_id,
            error_code=error_code,
            last_error=str(last_error),
            retry_count=retry_count,
            payload_json=payload,
            created_at=time.time()
        )
        self.db.add(dead_letter_job)

        # Update AgentRun status
        agent_run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if agent_run:
            agent_run.status = "FAILED"
            agent_run.updated_at = time.time()

        self.db.commit()
        self.db.refresh(dead_letter_job)
        logger.error(f"[DeadLetterManager] Moved run {run_id} to Dead-Letter Queue (DLQ ID: {job_id})")
        return dead_letter_job

    def list_dead_letter_jobs(self, user_id: Optional[int] = None) -> List[DeadLetterJob]:
        """Fetch all dead-letter jobs, optionally filtered by user."""
        query = self.db.query(DeadLetterJob)
        if user_id is not None:
            query = query.filter(DeadLetterJob.user_id == user_id)
        return query.order_by(DeadLetterJob.created_at.desc()).all()

    def retry_dead_letter_job(self, job_id: str) -> Optional[AgentRun]:
        """Manually requeue a dead-letter job for execution."""
        dl_job = self.db.query(DeadLetterJob).filter(DeadLetterJob.id == job_id).first()
        if not dl_job:
            logger.warning(f"[DeadLetterManager] Dead letter job {job_id} not found.")
            return None

        agent_run = self.db.query(AgentRun).filter(AgentRun.id == dl_job.run_id).first()
        if agent_run:
            agent_run.status = "QUEUED"
            agent_run.updated_at = time.time()
            self.db.delete(dl_job)
            self.db.commit()
            logger.info(f"[DeadLetterManager] Requeued run {agent_run.id} from DLQ.")
            return agent_run
        return None
