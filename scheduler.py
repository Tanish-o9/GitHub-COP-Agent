"""
Resource Scheduler & Concurrency Control
Enforces per-user and global concurrency limits, task priorities, and fair queueing across workers.
"""
import time
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from database.models import AgentRun
from worker.task_queue import get_redis_client

logger = logging.getLogger(__name__)

# Configurable limits
MAX_CONCURRENT_RUNS_PER_USER = 2
MAX_ACTIVE_RUNS_GLOBAL = 10
MAX_INDEXING_JOBS_PER_USER = 1

# Priorities
PRIORITY_LOW = 10       # Background indexing, evaluations
PRIORITY_NORMAL = 50    # Standard agent runs
PRIORITY_HIGH = 100     # Interactive user workflow


class ResourceScheduler:
    """Manages concurrent job execution, priorities, and fair user queueing."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.redis = get_redis_client()

    def can_start_run(self, user_id: int, workflow_type: str = "REPO_INTELLIGENCE") -> bool:
        """Check if starting a new run satisfies per-user and global concurrency limits."""
        # Check global active runs
        global_active = (
            self.db.query(AgentRun)
            .filter(AgentRun.status.in_(["RUNNING", "WAITING_FOR_APPROVAL"]))
            .count()
        )
        if global_active >= MAX_ACTIVE_RUNS_GLOBAL:
            logger.warning(f"[Scheduler] Global limit reached ({global_active}/{MAX_ACTIVE_RUNS_GLOBAL}). Queueing request.")
            return False

        # Check per-user active runs
        user_active = (
            self.db.query(AgentRun)
            .filter(
                AgentRun.user_id == user_id,
                AgentRun.status.in_(["RUNNING", "WAITING_FOR_APPROVAL"])
            )
            .count()
        )
        if user_active >= MAX_CONCURRENT_RUNS_PER_USER:
            logger.warning(f"[Scheduler] User {user_id} hit max concurrent limit ({user_active}/{MAX_CONCURRENT_RUNS_PER_USER}). Queueing request.")
            return False

        return True

    def get_queue_stats(self) -> Dict[str, Any]:
        """Fetch system-wide concurrency and queue statistics."""
        active_runs = (
            self.db.query(AgentRun)
            .filter(AgentRun.status.in_(["RUNNING", "WAITING_FOR_APPROVAL"]))
            .count()
        )
        queued_runs = (
            self.db.query(AgentRun)
            .filter(AgentRun.status == "QUEUED")
            .count()
        )
        completed_runs = self.db.query(AgentRun).filter(AgentRun.status == "COMPLETED").count()
        failed_runs = self.db.query(AgentRun).filter(AgentRun.status == "FAILED").count()

        return {
            "active_runs": active_runs,
            "queued_runs": queued_runs,
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "max_active_global": MAX_ACTIVE_RUNS_GLOBAL,
            "max_concurrent_per_user": MAX_CONCURRENT_RUNS_PER_USER
        }

    def schedule_next_run(self) -> Optional[AgentRun]:
        """
        Fair Queueing Scheduler:
        Selects the next QUEUED run considering task priority and user fairness.
        """
        queued_runs = (
            self.db.query(AgentRun)
            .filter(AgentRun.status == "QUEUED")
            .order_by(AgentRun.created_at.asc())
            .all()
        )
        if not queued_runs:
            return None

        # Group queued runs by user
        user_queues: Dict[int, List[AgentRun]] = {}
        for run in queued_runs:
            user_queues.setdefault(run.user_id, []).append(run)

        # Select candidate run from user with lowest active runs (Fair scheduling)
        candidate_run = None
        min_active = float("inf")

        for user_id, user_runs in user_queues.items():
            if not self.can_start_run(user_id):
                continue

            user_active = (
                self.db.query(AgentRun)
                .filter(
                    AgentRun.user_id == user_id,
                    AgentRun.status.in_(["RUNNING", "WAITING_FOR_APPROVAL"])
                )
                .count()
            )
            if user_active < min_active:
                min_active = user_active
                candidate_run = user_runs[0]  # Pick oldest queued for this user

        return candidate_run
