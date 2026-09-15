"""
Bounded Autonomy Policy Engine
Defines explicit autonomy levels (0 to 4), tool permissions, iteration caps, and risk thresholds.
Strictly prohibits level 5 unrestricted autonomous production mutation.
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Autonomy Level Constants
LEVEL_0_ANALYSIS_ONLY = 0
LEVEL_1_PLAN_ONLY = 1
LEVEL_2_CODE_AFTER_APPROVAL = 2
LEVEL_3_PR_AFTER_APPROVAL = 3
LEVEL_4_FEEDBACK_DRIVEN_REVISIONS = 4


@dataclass
class AutonomyPolicySpec:
    """Specification of constraints and bounds for an autonomy level."""
    level: int
    name: str
    description: str
    allowed_mutations: List[str] = field(default_factory=list)
    requires_human_approval: bool = True
    max_iterations: int = 3
    max_agent_calls: int = 20
    max_mcp_calls: int = 30
    max_files_changed: int = 5
    max_risk_threshold: float = 75.0  # High risk triggers mandatory approval

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AutonomyPolicyManager:
    """Manages system autonomy policies and enforces safe boundaries."""

    _policies: Dict[int, AutonomyPolicySpec] = {
        LEVEL_0_ANALYSIS_ONLY: AutonomyPolicySpec(
            level=LEVEL_0_ANALYSIS_ONLY,
            name="Analysis Only",
            description="Read-only repository investigation and RAG search. Zero mutations.",
            allowed_mutations=[],
            requires_human_approval=False,
            max_iterations=1,
            max_agent_calls=10,
            max_mcp_calls=20,
            max_files_changed=0,
            max_risk_threshold=100.0
        ),
        LEVEL_1_PLAN_ONLY: AutonomyPolicySpec(
            level=LEVEL_1_PLAN_ONLY,
            name="Plan Only",
            description="Formulates implementation plans and test impact reports. Zero code edits.",
            allowed_mutations=[],
            requires_human_approval=False,
            max_iterations=2,
            max_agent_calls=15,
            max_mcp_calls=25,
            max_files_changed=0,
            max_risk_threshold=100.0
        ),
        LEVEL_2_CODE_AFTER_APPROVAL: AutonomyPolicySpec(
            level=LEVEL_2_CODE_AFTER_APPROVAL,
            name="Code After Approval",
            description="Generates patch and commits to safe feature branch ONLY AFTER explicit human approval.",
            allowed_mutations=["create_branch", "commit_file_changes"],
            requires_human_approval=True,
            max_iterations=3,
            max_agent_calls=30,
            max_mcp_calls=50,
            max_files_changed=5,
            max_risk_threshold=50.0
        ),
        LEVEL_3_PR_AFTER_APPROVAL: AutonomyPolicySpec(
            level=LEVEL_3_PR_AFTER_APPROVAL,
            name="PR After Approval",
            description="Creates feature branch and opens GitHub PR ONLY AFTER explicit human approval.",
            allowed_mutations=["create_branch", "commit_file_changes", "create_pull_request"],
            requires_human_approval=True,
            max_iterations=3,
            max_agent_calls=40,
            max_mcp_calls=60,
            max_files_changed=8,
            max_risk_threshold=50.0
        ),
        LEVEL_4_FEEDBACK_DRIVEN_REVISIONS: AutonomyPolicySpec(
            level=LEVEL_4_FEEDBACK_DRIVEN_REVISIONS,
            name="Feedback-Driven Revisions",
            description="Revises existing approved feature branch PRs in response to CI failures or review comments.",
            allowed_mutations=["commit_file_changes"],
            requires_human_approval=True,
            max_iterations=3,
            max_agent_calls=50,
            max_mcp_calls=80,
            max_files_changed=10,
            max_risk_threshold=40.0
        ),
    }

    @classmethod
    def get_policy(cls, level: int) -> AutonomyPolicySpec:
        """Fetch policy specification for an autonomy level (defaults to LEVEL_2)."""
        return cls._policies.get(level, cls._policies[LEVEL_2_CODE_AFTER_APPROVAL])
