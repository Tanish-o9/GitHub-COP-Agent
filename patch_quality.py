"""
Patch Quality Evaluator
Evaluates proposed patches using explainable heuristics (correctness, test quality, security, maintainability, scope discipline).
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from semantic_diff import ChangeSummary
from risk_engine import RiskReport

logger = logging.getLogger(__name__)


@dataclass
class PatchQualityReport:
    """Detailed quality report for a proposed software patch."""
    quality_score: float  # 0.0 to 100.0
    correctness_score: float
    test_quality_score: float
    security_score: float
    maintainability_score: float
    scope_discipline_score: float
    blocking_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PatchQualityEvaluator:
    """Evaluates software patch quality against engineering heuristics."""

    def evaluate_patch(
        self,
        change_summary: ChangeSummary,
        risk_report: Optional[RiskReport] = None,
        test_passed: bool = True,
        security_passed: bool = True
    ) -> PatchQualityReport:
        correctness = 90.0 if test_passed else 30.0
        test_quality = 85.0 if change_summary.test_changes else 40.0
        security = 95.0 if security_passed else 20.0
        maintainability = 85.0
        scope_discipline = 90.0 if len(change_summary.files_changed) <= 3 else 60.0

        blocking = []
        warnings = []
        recs = []

        if not test_passed:
            blocking.append("Automated unit tests failed for proposed patch")
        if not security_passed:
            blocking.append("Security gate audit flagged vulnerability or unredacted secret")

        if not change_summary.test_changes:
            warnings.append("Patch does not include accompanying unit test updates")
            recs.append("Add unit tests covering modified functions")

        if len(change_summary.files_changed) > 5:
            warnings.append("Large PR footprint spanning more than 5 files")
            recs.append("Consider breaking change into smaller atomic PRs")

        overall_score = round(
            (correctness * 0.3) +
            (test_quality * 0.25) +
            (security * 0.25) +
            (maintainability * 0.1) +
            (scope_discipline * 0.1),
            1
        )

        return PatchQualityReport(
            quality_score=overall_score,
            correctness_score=correctness,
            test_quality_score=test_quality,
            security_score=security,
            maintainability_score=maintainability,
            scope_discipline_score=scope_discipline,
            blocking_issues=blocking,
            warnings=warnings,
            recommendations=recs
        )
