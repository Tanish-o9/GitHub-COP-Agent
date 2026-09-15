"""
Workflow State Transition Validator Module
Validates allowed state machine transitions and blocks illegal state jumps.
"""
from typing import Dict, Any, List, Set


class StateValidator:
    """
    Validates state machine transitions for the engineering workflow.
    """

    ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
        "PENDING": {"ANALYZING", "FAILED", "CANCELLED"},
        "ANALYZING": {"PLANNING", "FAILED", "CANCELLED"},
        "PLANNING": {"IMPLEMENTING", "WAITING_FOR_APPROVAL", "FAILED", "CANCELLED"},
        "IMPLEMENTING": {"TESTING", "REVISION_REQUIRED", "FAILED", "CANCELLED"},
        "TESTING": {"REVIEWING", "REVISION_REQUIRED", "FAILED", "CANCELLED"},
        "REVIEWING": {"SECURITY_CHECK", "REVISION_REQUIRED", "FAILED", "CANCELLED"},
        "REVISION_REQUIRED": {"IMPLEMENTING", "FAILED", "CANCELLED"},
        "SECURITY_CHECK": {"WAITING_FOR_APPROVAL", "FAILED", "CANCELLED"},
        "WAITING_FOR_APPROVAL": {"READY_FOR_PR", "PR_CREATED", "CANCELLED", "FAILED"},
        "READY_FOR_PR": {"PR_CREATED", "CANCELLED", "FAILED"},
        "PR_CREATED": {"COMPLETED"},
        "FAILED": set(),
        "CANCELLED": set(),
        "COMPLETED": set()
    }

    @classmethod
    def validate_transition(cls, current: Any, target: Any) -> bool:
        """Check if transition from current to target state is valid."""
        curr_str = str(current.value if hasattr(current, "value") else current)
        target_str = str(target.value if hasattr(target, "value") else target)

        allowed = cls.ALLOWED_TRANSITIONS.get(curr_str, set())
        if target_str not in allowed and curr_str != target_str:
            raise ValueError(f"❌ Invalid Workflow State Transition: Illegal jump from `{curr_str}` to `{target_str}`.")
        return True
