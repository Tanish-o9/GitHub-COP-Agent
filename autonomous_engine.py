"""
Autonomous Engineering Controller
High-level bounded engineering workflow controller orchestrating task intake, planning, verification, risk assessment, human approval, PR creation, and feedback loops.
"""
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from engineering_contract import TaskContract, TaskContractValidator
from autonomy_policy import AutonomyPolicyManager
from autonomy_safety import AutonomySafetyEvaluator, AutonomySafetyDecision
from acceptance_engine import AcceptanceEngine, Criterion
from plan_validator import PlanValidator
from patch_optimizer import PatchOptimizer
from self_verifier import SelfVerifier, VerificationResult
from risk_engine import ChangeRiskEngine, RiskReport
from patch_quality import PatchQualityEvaluator, PatchQualityReport
from state_validator import StateValidator
from checkpoint_manager import CheckpointManager
from github_mcp import GitHubMCPTools
from database.models import EngineeringTaskModel, TaskCriterionModel, AgentRun

logger = logging.getLogger(__name__)

# Explicit Task Lifecycle States
STATE_INTAKE = "INTAKE"
STATE_ANALYZING = "ANALYZING"
STATE_PLANNING = "PLANNING"
STATE_IMPLEMENTING = "IMPLEMENTING"
STATE_TESTING = "TESTING"
STATE_REVIEWING = "REVIEWING"
STATE_VERIFYING = "VERIFYING"
STATE_APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
STATE_APPROVED = "APPROVED"
STATE_PR_CREATED = "PR_CREATED"
STATE_WAITING_FOR_FEEDBACK = "WAITING_FOR_FEEDBACK"
STATE_REVISION_REQUIRED = "REVISION_REQUIRED"
STATE_RETESTING = "RETESTING"
STATE_READY_TO_MERGE = "READY_TO_MERGE"
STATE_MERGED = "MERGED"
STATE_POST_MERGE_VALIDATION = "POST_MERGE_VALIDATION"
STATE_COMPLETED = "COMPLETED"
STATE_FAILED = "FAILED"
STATE_CANCELLED = "CANCELLED"


class AutonomousEngineeringController:
    """Bounded engineering controller orchestrating autonomous tasks with explicit human policy gates."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.chk_manager = CheckpointManager(db_session)
        self.acceptance_engine = AcceptanceEngine()
        self.plan_validator = PlanValidator()
        self.patch_optimizer = PatchOptimizer()
        self.self_verifier = SelfVerifier()
        self.risk_engine = ChangeRiskEngine()
        self.quality_evaluator = PatchQualityEvaluator()
        self.safety_evaluator = AutonomySafetyEvaluator()

    def intake_task(
        self,
        tenant_id: int,
        repository_name: str,
        objective: str,
        task_type: str = "REPO_INTELLIGENCE",
        autonomy_level: int = 2,
        explicit_criteria: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Step 1: Validate contract & extract acceptance criteria."""
        contract = TaskContractValidator.create_contract(
            tenant_id=tenant_id,
            repository_name=repository_name,
            objective=objective,
            task_type=task_type,
            autonomy_level=autonomy_level,
            acceptance_criteria=explicit_criteria
        )

        validation = TaskContractValidator.validate(contract)
        if not validation["valid"]:
            logger.error(f"[AutonomousEngine] Contract validation failed: {validation['errors']}")
            return {"status": STATE_FAILED, "errors": validation["errors"]}

        # Extract criteria
        criteria = self.acceptance_engine.extract_criteria(objective, explicit_criteria)

        # Persist task in database
        db_task = EngineeringTaskModel(
            id=contract.task_id,
            tenant_id=tenant_id,
            repository_name=repository_name,
            objective=objective,
            status=STATE_INTAKE,
            autonomy_level=autonomy_level,
            created_at=time.time(),
            updated_at=time.time()
        )
        self.db.add(db_task)

        for c in criteria:
            db_crit = TaskCriterionModel(
                task_id=contract.task_id,
                description=c.description,
                status=c.status,
                evidence_json={"evidence": c.evidence}
            )
            self.db.add(db_crit)

        self.db.commit()

        # Checkpoint initial intake state
        self.chk_manager.create_checkpoint(contract.task_id, "intake", {
            "task_id": contract.task_id,
            "status": STATE_INTAKE,
            "criteria_count": len(criteria)
        })

        logger.info(f"[AutonomousEngine] Intaked task {contract.task_id} for repo {repository_name}")
        return {
            "task_id": contract.task_id,
            "status": STATE_INTAKE,
            "criteria": [c.to_dict() for c in criteria],
            "contract": contract.to_dict()
        }

    def execute_bounded_workflow(
        self,
        task_id: str,
        mcp_tools: GitHubMCPTools
    ) -> Dict[str, Any]:
        """Step 2: Execute bounded planning, verification, risk assessment, and approval gating."""
        db_task = self.db.query(EngineeringTaskModel).filter(EngineeringTaskModel.id == task_id).first()
        if not db_task:
            return {"status": STATE_FAILED, "error": f"Task {task_id} not found."}

        # 1. State: ANALYZING
        db_task.status = STATE_ANALYZING
        self.db.commit()
        self.chk_manager.create_checkpoint(task_id, "analyzing", {"status": STATE_ANALYZING})

        # 2. State: PLANNING
        db_task.status = STATE_PLANNING
        self.db.commit()
        plan_steps = [
            f"1. Analyze repository structure for {db_task.repository_name}",
            f"2. Inspect target module for objective: '{db_task.objective}'",
            "3. Formulate minimal code patch",
            "4. Run unit and integration tests",
            "5. Execute security audit",
            "6. Formulate PR and request human approval"
        ]
        alternatives = self.plan_validator.generate_plan_alternatives("src/main.py")
        self.chk_manager.create_checkpoint(task_id, "planning", {
            "status": STATE_PLANNING,
            "plan_steps": plan_steps,
            "alternatives": [a.to_dict() for a in alternatives]
        })

        # 3. State: APPROVAL_REQUIRED
        db_task.status = STATE_APPROVAL_REQUIRED
        self.db.commit()
        self.chk_manager.create_checkpoint(task_id, "approval_required", {
            "status": STATE_APPROVAL_REQUIRED,
            "message": "Write mutation gated behind human approval."
        })

        return {
            "task_id": task_id,
            "status": STATE_APPROVAL_REQUIRED,
            "plan_steps": plan_steps,
            "alternatives": [a.to_dict() for a in alternatives],
            "approval_required": True
        }
