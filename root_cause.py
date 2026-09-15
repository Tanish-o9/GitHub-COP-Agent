"""
Root Cause Analysis Engine
Evaluates CI failures, stack traces, and diffs to generate evidence-grounded RootCauseReports with explicit confidence ratings.
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from ci_failure_analyzer import ParsedCIFailure

logger = logging.getLogger(__name__)


@dataclass
class RootCauseReport:
    """Root cause diagnosis report with confidence level and recommendations."""
    failure_summary: str
    hypotheses: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE
    recommended_fix: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RootCauseEngine:
    """Diagnoses root cause hypotheses for CI and test failures based on trace empirical evidence."""

    def analyze_root_cause(
        self,
        failure: ParsedCIFailure,
        recent_diff_symbols: Optional[List[str]] = None
    ) -> RootCauseReport:
        hypotheses = []
        evidence = []
        recent_diff_symbols = recent_diff_symbols or []

        if failure.error_message:
            evidence.append(f"CI Log Exception: '{failure.error_message}'")
        if failure.target_file:
            evidence.append(f"Traceback location: `{failure.target_file}:L{failure.line_number}`")

        # Formulate root cause hypotheses
        if "KeyError" in failure.error_message:
            hypotheses.append(f"Missing dictionary key or environment variable access in `{failure.target_file}`")
            fix = f"Add key check or default fallback in `{failure.target_file}` at L{failure.line_number}"
            conf = "HIGH"
        elif "AssertionError" in failure.error_message:
            hypotheses.append(f"Behavioral mismatch in `{failure.failing_test}` comparing expected vs actual output")
            fix = f"Update logic in `{failure.target_file}` or adjust test assertions in `{failure.failing_test}`"
            conf = "HIGH"
        elif recent_diff_symbols:
            hypotheses.append(f"Recent modification to symbol '{recent_diff_symbols[0]}' broke test contracts")
            fix = f"Revert or adjust implementation of '{recent_diff_symbols[0]}'"
            conf = "MEDIUM"
        else:
            hypotheses.append("Uncertain root cause — insufficient trace details")
            fix = "Run local debugger or add verbose logging to pinpoint root cause"
            conf = "INSUFFICIENT_EVIDENCE"

        return RootCauseReport(
            failure_summary=f"Failure in '{failure.failing_test}': {failure.error_message}",
            hypotheses=hypotheses,
            evidence=evidence,
            confidence=conf,
            recommended_fix=fix
        )
