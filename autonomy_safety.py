"""
Autonomy Safety Evaluator
Policy-driven safety decision engine determining whether an autonomous action is SAFE_TO_PROCEED, REQUIRES_APPROVAL, or BLOCKED.
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from engineering_contract import TaskContract
from autonomy_policy import AutonomyPolicyManager

logger = logging.getLogger(__name__)


@dataclass
class AutonomySafetyDecision:
    """Represents a policy safety decision for an engineering task action."""
    decision: str  # SAFE_TO_PROCEED, REQUIRES_APPROVAL, BLOCKED
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AutonomySafetyEvaluator:
    """Evaluates task safety against policy boundaries, risk scores, and security findings."""

    def evaluate(
        self,
        contract: TaskContract,
        risk_score: float = 0.0,
        security_passed: bool = True,
        budget_exceeded: bool = False,
        is_mutation_operation: bool = False
    ) -> AutonomySafetyDecision:
        reasons = []
        policy = AutonomyPolicyManager.get_policy(contract.autonomy_level)

        # 1. Hard Budget Exhaustion
        if budget_exceeded:
            reasons.append("Resource budget limit reached for this task.")
            return AutonomySafetyDecision(decision="BLOCKED", reasons=reasons)

        # 2. Security Gate Failure
        if not security_passed:
            reasons.append("Security audit failed (unredacted secret or vulnerability detected).")
            return AutonomySafetyDecision(decision="BLOCKED", reasons=reasons)

        # 3. High Risk Exceeds Autonomy Threshold
        if risk_score >= policy.max_risk_threshold:
            reasons.append(f"Risk score ({risk_score}) exceeds policy threshold ({policy.max_risk_threshold}).")
            return AutonomySafetyDecision(decision="REQUIRES_APPROVAL", reasons=reasons)

        # 4. Write Mutation Operations Require Mandatory Approval
        if is_mutation_operation or policy.requires_human_approval:
            reasons.append(f"Autonomy Policy Level {policy.level} ({policy.name}) requires explicit human approval for write mutations.")
            return AutonomySafetyDecision(decision="REQUIRES_APPROVAL", reasons=reasons)

        reasons.append("Read-only analysis task satisfies policy bounds.")
        return AutonomySafetyDecision(decision="SAFE_TO_PROCEED", reasons=reasons)
