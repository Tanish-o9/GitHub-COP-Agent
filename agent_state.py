"""
Agent State Module — Phase 4
Centralized shared state and validated workflow state machine definitions.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from state_validator import StateValidator


class WorkflowState(str, Enum):
    """Explicit workflow execution states."""
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    IMPLEMENTING = "IMPLEMENTING"
    TESTING = "TESTING"
    REVIEWING = "REVIEWING"
    SECURITY_CHECK = "SECURITY_CHECK"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    READY_FOR_PR = "READY_FOR_PR"
    PR_CREATED = "PR_CREATED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


@dataclass
class AgentState:
    """
    Shared context container passed across agents during workflow execution.
    """
    user_request: str
    repo_name: str
    branch: str = "main"
    issue_number: Optional[int] = None
    pr_number: Optional[int] = None

    # Context & Intelligence Data
    repo_structure: List[Dict[str, Any]] = field(default_factory=list)
    relevant_files: List[Dict[str, Any]] = field(default_factory=list)
    code_context: Dict[str, str] = field(default_factory=dict)
    
    # Analysis & Planning
    issue_analysis: Dict[str, Any] = field(default_factory=dict)
    root_cause: str = ""
    implementation_plan: List[str] = field(default_factory=list)

    # Modifications & Testing
    proposed_changes: Dict[str, Any] = field(default_factory=dict)
    generated_tests: Dict[str, Any] = field(default_factory=dict)
    test_results: Dict[str, Any] = field(default_factory=dict)

    # Reviews & Security
    review_findings: Dict[str, Any] = field(default_factory=dict)
    security_findings: Dict[str, Any] = field(default_factory=dict)
    
    # Execution Tracking
    current_state: WorkflowState = WorkflowState.PENDING
    revision_count: int = 0
    max_revisions: int = 3
    approval_status: str = "PENDING"
    
    # Git & PR Outputs
    branch_name: str = ""
    commit_info: List[Dict[str, Any]] = field(default_factory=list)
    pr_info: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def transition_to(self, new_state: WorkflowState, note: Optional[str] = None) -> None:
        """Validated state transition helper."""
        StateValidator.validate_transition(self.current_state, new_state)
        self.current_state = new_state

    def add_error(self, error_msg: str) -> None:
        """Record workflow error."""
        self.errors.append(error_msg)
        self.current_state = WorkflowState.FAILED

    def to_summary_dict(self) -> Dict[str, Any]:
        """Summary for UI display and tracing."""
        return {
            "current_state": self.current_state.value,
            "repo_name": self.repo_name,
            "branch": self.branch,
            "issue_number": self.issue_number,
            "revision_count": self.revision_count,
            "files_modified": list(self.proposed_changes.keys()),
            "errors": self.errors
        }
