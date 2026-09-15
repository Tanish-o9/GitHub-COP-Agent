"""
Adaptive Test Selector
Selects optimal test suites based on execution modes (FAST, BALANCED, DEEP) and change risk footprint.
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from regression_engine import RegressionRiskReport

logger = logging.getLogger(__name__)

MODE_FAST = "FAST"
MODE_BALANCED = "BALANCED"
MODE_DEEP = "DEEP"


@dataclass
class TestExecutionPlan:
    """Test execution plan tailored to execution mode and risk footprint."""
    mode: str  # FAST, BALANCED, DEEP
    selected_tests: List[str] = field(default_factory=list)
    estimated_duration_sec: float = 5.0
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AdaptiveTestSelector:
    """ Tailors test execution depth based on adaptive modes and risk levels."""

    def select_tests(
        self,
        changed_files: List[str],
        risk_report: Optional[RegressionRiskReport] = None,
        requested_mode: str = MODE_BALANCED
    ) -> TestExecutionPlan:
        selected = []
        reasons = []

        # Auto-escalate FAST -> BALANCED if risk is HIGH/CRITICAL
        mode = requested_mode
        if risk_report and risk_report.risk_level in ["HIGH", "CRITICAL"] and mode == MODE_FAST:
            mode = MODE_BALANCED
            reasons.append(f"Auto-escalated execution mode to {MODE_BALANCED} due to {risk_report.risk_level} risk level.")

        # 1. Directly affected tests (Convention & Graph)
        for f in changed_files:
            basename = f.split("/")[-1].replace(".py", "")
            selected.append(f"tests/test_{basename}.py")

        if mode in [MODE_BALANCED, MODE_DEEP]:
            selected.append("tests/test_phase4.py")
            selected.append("tests/test_phase5.py")
            reasons.append("Added Phase 4/5 security and architecture regression suites.")

        if mode == MODE_DEEP:
            selected.append("scratch/test_phase6.py")
            selected.append("scratch/test_phase7.py")
            reasons.append("Added full system Phase 6/7 integration test suites.")

        duration = len(selected) * 2.5
        reasons.append(f"Selected {len(selected)} test suites under '{mode}' mode.")

        return TestExecutionPlan(
            mode=mode,
            selected_tests=list(set(selected)),
            estimated_duration_sec=round(duration, 1),
            reasons=reasons
        )
