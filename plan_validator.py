"""
Plan Validator & Alternatives Generator
Validates engineering plans against acceptance criteria and formulates plan alternatives (Minimal Patch, Refactor, Architectural Change).
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from acceptance_engine import Criterion

logger = logging.getLogger(__name__)


@dataclass
class PlanApproach:
    """Represents an alternative plan approach with complexity and risk trade-offs."""
    name: str
    description: str
    complexity_score: float  # 0.0 to 100.0
    risk_level: str          # LOW, MEDIUM, HIGH
    recommended: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PlanValidator:
    """Validates implementation plans prior to code execution."""

    def validate_plan(
        self,
        plan_steps: List[str],
        criteria: List[Criterion],
        has_security_step: bool = True
    ) -> Dict[str, Any]:
        errors = []
        warnings = []

        if not plan_steps:
            errors.append("Implementation plan cannot be empty.")
        if len(plan_steps) < 2:
            warnings.append("Plan contains very few steps (<2).")

        # Check if plan references tests
        plan_text = " ".join(plan_steps).lower()
        if "test" not in plan_text:
            warnings.append("Implementation plan does not explicitly reference testing steps.")

        if not has_security_step and any("auth" in c.description.lower() for c in criteria):
            errors.append("Security-critical task lacks explicit security audit step in plan.")

        is_valid = len(errors) == 0
        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "steps_count": len(plan_steps)
        }

    def generate_plan_alternatives(self, target_file: str) -> List[PlanApproach]:
        """Formulate plan approaches (Minimal Patch, Refactor, Architectural Change)."""
        return [
            PlanApproach(
                name="Approach A: Minimal Patch",
                description=f"In-place bug fix in `{target_file}` with zero structural refactoring.",
                complexity_score=20.0,
                risk_level="LOW",
                recommended=True
            ),
            PlanApproach(
                name="Approach B: Modular Refactor",
                description=f"Refactor target functions in `{target_file}` into decoupled helper functions.",
                complexity_score=50.0,
                risk_level="MEDIUM",
                recommended=False
            ),
            PlanApproach(
                name="Approach C: Architectural Interface Redesign",
                description=f"Introduce new abstract class/interface layer across `{target_file}` and callers.",
                complexity_score=85.0,
                risk_level="HIGH",
                recommended=False
            )
        ]
