"""
Checkpoint Manager
Handles durable checkpoint persistence and worker recovery.
Saves agent workflow state after each step and restores execution state upon worker restart.
"""
import time
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from database.models import AgentCheckpoint, AgentRun

logger = logging.getLogger(__name__)

# Keys to sanitize from state checkpoints (secrets, tokens, sensitive internal thoughts)
SENSITIVE_KEYS = {"token", "password", "secret", "github_token", "jwt_secret", "chain_of_thought"}


def _sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively strip sensitive keys and hidden chain-of-thought from state."""
    clean = {}
    for k, v in data.items():
        if any(sk in k.lower() for sk in SENSITIVE_KEYS):
            clean[k] = "[REDACTED]"
        elif isinstance(v, dict):
            clean[k] = _sanitize_dict(v)
        elif isinstance(v, list):
            clean[k] = [_sanitize_dict(item) if isinstance(item, dict) else item for item in v]
        else:
            clean[k] = v
    return clean


class CheckpointManager:
    """Manages durable state checkpoints for Agent Runs."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def create_checkpoint(self, run_id: str, step_name: str, state_data: Dict[str, Any], status: str = "COMPLETED") -> AgentCheckpoint:
        """Persist a clean checkpoint to PostgreSQL/SQLite."""
        sanitized_state = _sanitize_dict(state_data)
        checkpoint = AgentCheckpoint(
            run_id=run_id,
            step_name=step_name,
            status=status,
            state_json=sanitized_state,
            created_at=time.time()
        )
        self.db.add(checkpoint)
        self.db.commit()
        self.db.refresh(checkpoint)
        logger.info(f"[CheckpointManager] Saved checkpoint for run {run_id} at step '{step_name}'")
        return checkpoint

    def get_latest_checkpoint(self, run_id: str) -> Optional[AgentCheckpoint]:
        """Fetch the most recent valid checkpoint for a run."""
        return (
            self.db.query(AgentCheckpoint)
            .filter(AgentCheckpoint.run_id == run_id)
            .order_by(AgentCheckpoint.created_at.desc())
            .first()
        )

    def get_all_checkpoints(self, run_id: str) -> List[AgentCheckpoint]:
        """Fetch all chronological checkpoints for a run."""
        return (
            self.db.query(AgentCheckpoint)
            .filter(AgentCheckpoint.run_id == run_id)
            .order_by(AgentCheckpoint.created_at.asc())
            .all()
        )

    def resume_run_state(self, run_id: str) -> Dict[str, Any]:
        """Reconstruct state from the latest checkpoint for worker recovery."""
        checkpoint = self.get_latest_checkpoint(run_id)
        if not checkpoint:
            logger.info(f"[CheckpointManager] No checkpoint found for run {run_id}. Starting fresh.")
            return {"run_id": run_id, "resumed": False, "last_completed_step": None}
        
        logger.info(f"[CheckpointManager] Resuming run {run_id} from step '{checkpoint.step_name}'")
        resumed_state = checkpoint.state_json or {}
        resumed_state["resumed"] = True
        resumed_state["last_completed_step"] = checkpoint.step_name
        return resumed_state
