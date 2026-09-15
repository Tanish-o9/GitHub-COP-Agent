"""
Acceptance Criteria Engine
Parses natural language requirements into structured acceptance criteria and tracks verification status (PASS, FAIL, UNKNOWN, NOT_APPLICABLE).
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class Criterion:
    """Represents a single verifiable acceptance criterion."""
    id: str
    description: str
    status: str = STATUS_UNKNOWN  # PASS, FAIL, UNKNOWN, NOT_APPLICABLE
    evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AcceptanceEngine:
    """Extracts and verifies acceptance criteria from user objectives."""

    def extract_criteria(self, objective: str, explicit_criteria: Optional[List[str]] = None) -> List[Criterion]:
        criteria = []

        # Convert explicit list if provided
        if explicit_criteria:
            for i, desc in enumerate(explicit_criteria, 1):
                criteria.append(Criterion(id=f"AC-{i}", description=desc, status=STATUS_UNKNOWN))
            return criteria

        # Auto-extract criteria from objective text
        obj_lower = objective.lower()
        idx = 1

        if any(w in obj_lower for w in ["fix", "bug", "error", "issue", "crash"]):
            criteria.append(Criterion(id=f"AC-{idx}", description="Root cause identified and target error eliminated", status=STATUS_UNKNOWN))
            idx += 1
            criteria.append(Criterion(id=f"AC-{idx}", description="Existing unit test suites pass without regression", status=STATUS_UNKNOWN))
            idx += 1

        if any(w in obj_lower for w in ["test", "coverage"]):
            criteria.append(Criterion(id=f"AC-{idx}", description="New or updated test cases added covering changed functions", status=STATUS_UNKNOWN))
            idx += 1

        if any(w in obj_lower for w in ["security", "auth", "secret"]):
            criteria.append(Criterion(id=f"AC-{idx}", description="Security gate audit passes with zero secret disclosures or OWASP risks", status=STATUS_UNKNOWN))
            idx += 1

        if not criteria:
            criteria.append(Criterion(id="AC-1", description=f"Objective satisfied: '{objective}'", status=STATUS_UNKNOWN))

        return criteria

    def update_criterion_status(self, criteria: List[Criterion], criterion_id: str, new_status: str, evidence: str = "") -> List[Criterion]:
        """Update status of a specific criterion."""
        for c in criteria:
            if c.id == criterion_id:
                c.status = new_status
                c.evidence = evidence
                logger.info(f"[AcceptanceEngine] Updated criterion {criterion_id} -> {new_status}")
        return criteria
