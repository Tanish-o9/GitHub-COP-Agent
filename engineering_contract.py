"""
Engineering Task Contract Module
Validates task metadata, objectives, acceptance criteria, constraints, and autonomy budgets before execution.
"""
import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from autonomy_policy import AutonomyPolicyManager, LEVEL_2_CODE_AFTER_APPROVAL

logger = logging.getLogger(__name__)


@dataclass
class TaskContract:
    """Structured contract defining requirements and bounds for an engineering task."""
    task_id: str
    tenant_id: int
    repository_name: str
    objective: str
    task_type: str = "REPO_INTELLIGENCE"
    autonomy_level: int = LEVEL_2_CODE_AFTER_APPROVAL
    constraints: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    max_budget_calls: int = 50

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TaskContractValidator:
    """Validates task contracts prior to execution."""

    @staticmethod
    def create_contract(
        tenant_id: int,
        repository_name: str,
        objective: str,
        task_type: str = "REPO_INTELLIGENCE",
        autonomy_level: int = LEVEL_2_CODE_AFTER_APPROVAL,
        constraints: Optional[List[str]] = None,
        acceptance_criteria: Optional[List[str]] = None
    ) -> TaskContract:
        task_id = f"TASK-{uuid.uuid4().hex[:8].upper()}"
        return TaskContract(
            task_id=task_id,
            tenant_id=tenant_id,
            repository_name=repository_name,
            objective=objective,
            task_type=task_type,
            autonomy_level=autonomy_level,
            constraints=constraints or [],
            acceptance_criteria=acceptance_criteria or []
        )

    @staticmethod
    def validate(contract: TaskContract) -> Dict[str, Any]:
        """Validate task contract parameters."""
        errors = []
        if not contract.objective or not contract.objective.strip():
            errors.append("Task objective cannot be empty.")
        if not contract.repository_name or "/" not in contract.repository_name:
            errors.append("Invalid repository_name format (expected owner/repo).")
        if contract.tenant_id <= 0:
            errors.append("Invalid tenant_id.")

        policy = AutonomyPolicyManager.get_policy(contract.autonomy_level)
        if not policy:
            errors.append(f"Invalid autonomy level: {contract.autonomy_level}")

        is_valid = len(errors) == 0
        return {
            "valid": is_valid,
            "errors": errors,
            "policy": policy.to_dict() if policy else None
        }
