"""
Human Approval Checkpoint Module
Manages approval requests and states for repository write operations.
"""
from typing import Dict, Any, List, Optional
from enum import Enum


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class HumanApprovalRequest:
    """
    Encapsulates a pending repository write action needing user approval.
    """

    def __init__(
        self,
        action_type: str, # e.g. "CREATE_BRANCH_AND_COMMIT", "CREATE_PULL_REQUEST"
        repo_name: str,
        target_branch: str,
        files_to_change: List[str],
        change_summary: str,
        generated_tests: List[str],
        potential_risks: List[str],
        patch_payload: Optional[Dict[str, Any]] = None
    ):
        self.action_type = action_type
        self.repo_name = repo_name
        self.target_branch = target_branch
        self.files_to_change = files_to_change
        self.change_summary = change_summary
        self.generated_tests = generated_tests
        self.potential_risks = potential_risks
        self.patch_payload = patch_payload or {}
        self.status = ApprovalStatus.PENDING

    def approve(self) -> None:
        """Mark change proposal as approved."""
        self.status = ApprovalStatus.APPROVED

    def reject(self) -> None:
        """Mark change proposal as rejected."""
        self.status = ApprovalStatus.REJECTED

    def to_dict(self) -> Dict[str, Any]:
        """Format approval details for Streamlit UI card display."""
        return {
            "action_type": self.action_type,
            "repo_name": self.repo_name,
            "target_branch": self.target_branch,
            "files_to_change": self.files_to_change,
            "change_summary": self.change_summary,
            "generated_tests": self.generated_tests,
            "potential_risks": self.potential_risks,
            "status": self.status.value,
            "patch_payload": self.patch_payload
        }
