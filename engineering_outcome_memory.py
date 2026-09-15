"""
Engineering Outcome Memory
Records task execution outcomes, plan effectiveness, review feedback patterns, and patch quality scores without storing secrets.
"""
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from engineering_memory_v2 import EngineeringMemoryV2

logger = logging.getLogger(__name__)


@dataclass
class OutcomeRecord:
    """Record of an executed engineering task outcome."""
    task_id: str
    repository_name: str
    objective: str
    patch_quality_score: float
    risk_score: float
    outcome_status: str  # SUCCESS, FAILED, REJECTED
    learnings: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EngineeringOutcomeMemory:
    """Manages persistent outcome memory records across engineering task runs."""

    def __init__(self, repository_name: str):
        self.repository_name = repository_name
        self.memory_v2 = EngineeringMemoryV2(repository_name)
        self.records: List[OutcomeRecord] = []

    def record_outcome(
        self,
        task_id: str,
        objective: str,
        patch_quality_score: float,
        risk_score: float,
        outcome_status: str = "SUCCESS",
        learnings: Optional[List[str]] = None
    ) -> OutcomeRecord:
        learnings_list = learnings or []

        rec = OutcomeRecord(
            task_id=task_id,
            repository_name=self.repository_name,
            objective=objective,
            patch_quality_score=patch_quality_score,
            risk_score=risk_score,
            outcome_status=outcome_status,
            learnings=learnings_list,
            timestamp=time.time()
        )
        self.records.append(rec)

        # Store learnings in memory v2 under HISTORY
        fact_msg = f"Task '{objective}' completed with status '{outcome_status}' (Quality: {patch_quality_score}, Risk: {risk_score})"
        self.memory_v2.add_memory("HISTORY", fact_msg, confidence=0.9, source="outcome_tracker")

        logger.info(f"[OutcomeMemory] Recorded outcome for task {task_id} on {self.repository_name}")
        return rec

    def get_repo_outcomes(self) -> List[OutcomeRecord]:
        return self.records
