"""
Regression Risk Predictor
Estimates regression risk using change footprint, dependency fanout, security sensitivity, and test coverage metrics.
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from code_graph import CodeIntelligenceGraph

logger = logging.getLogger(__name__)


@dataclass
class RegressionRiskReport:
    """Report detailing regression risk scores and recommended verification test suites."""
    regression_score: float  # 0.0 to 100.0
    risk_level: str          # LOW, MEDIUM, HIGH, CRITICAL
    reasons: List[str] = field(default_factory=list)
    recommended_tests: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RegressionRiskPredictor:
    """Predicts regression risk for proposed code changes."""

    def predict_risk(
        self,
        changed_files: List[str],
        code_graph: Optional[CodeIntelligenceGraph] = None,
        test_count: int = 0
    ) -> RegressionRiskReport:
        score = 0.0
        reasons = []
        recs = []

        files_count = len(changed_files)
        score += min(40.0, files_count * 8.0)
        if files_count > 3:
            reasons.append(f"Multiple files ({files_count}) modified simultaneously")

        # Dependency fanout check
        fanout = 0
        if code_graph:
            for f in changed_files:
                impact = code_graph.get_affected_nodes(f)
                fanout += len(impact.get("direct_dependent_files", []))
            if fanout > 3:
                score += 30.0
                reasons.append(f"High caller fanout across {fanout} dependent files")

        if any("auth" in f or "security" in f or "api/" in f for f in changed_files):
            score += 25.0
            reasons.append("Modification to security or public API boundary module")

        if test_count == 0:
            score += 20.0
            reasons.append("Zero accompanying test modifications recorded")

        score = min(100.0, score)
        if score >= 75.0:
            level = "CRITICAL"
        elif score >= 50.0:
            level = "HIGH"
        elif score >= 25.0:
            level = "MEDIUM"
        else:
            level = "LOW"

        for f in changed_files:
            basename = f.split("/")[-1].replace(".py", "")
            recs.append(f"tests/test_{basename}.py")

        return RegressionRiskReport(
            regression_score=round(score, 1),
            risk_level=level,
            reasons=reasons or ["Low regression risk: Isolated change"],
            recommended_tests=recs
        )
