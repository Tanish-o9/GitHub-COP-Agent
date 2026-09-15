"""
Change Risk Engine
Calculates explainable change-risk score (0-100) and risk level (LOW, MEDIUM, HIGH, CRITICAL) with human-readable rationale.
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from semantic_diff import ChangeSummary
from code_graph import CodeIntelligenceGraph

logger = logging.getLogger(__name__)


@dataclass
class RiskReport:
    """Explainable risk assessment report for code changes."""
    risk_score: float  # 0.0 to 100.0
    risk_level: str    # LOW, MEDIUM, HIGH, CRITICAL
    reasons: List[str] = field(default_factory=list)
    affected_dependents_count: int = 0
    missing_tests: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ChangeRiskEngine:
    """Evaluates change risks based on semantic diffs and graph dependency centrality."""

    def evaluate_risk(
        self,
        change_summary: ChangeSummary,
        code_graph: Optional[CodeIntelligenceGraph] = None
    ) -> RiskReport:
        score = 0.0
        reasons = []
        dependents_count = 0
        missing_tests = False

        # 1. File Count Scope
        files_count = len(change_summary.files_changed)
        if files_count >= 10:
            score += 25.0
            reasons.append(f"Large change footprint: {files_count} files modified")
        elif files_count >= 5:
            score += 15.0
            reasons.append(f"Moderate change footprint: {files_count} files modified")

        # 2. Risk Factors from Diff
        for factor in change_summary.risk_factors:
            score += 15.0
            reasons.append(f"Risk factor: {factor}")

        # 3. Security & Schema Modifications
        if change_summary.behavior_changes:
            score += 25.0
            reasons.append("Security or authentication behavior logic modified")
        if change_summary.schema_changes:
            score += 20.0
            reasons.append("Database schema models modified")

        # 4. Dependency Graph Centrality Check
        if code_graph:
            for file_path in change_summary.files_changed:
                impact = code_graph.get_affected_nodes(file_path)
                dependents_count += len(impact.get("direct_dependent_files", []))
            
            if dependents_count > 5:
                score += 20.0
                reasons.append(f"High caller fanout: {dependents_count} dependent files affected")

        # 5. Test Coverage Check
        if not change_summary.test_changes and any("src/" in f or "api/" in f for f in change_summary.files_changed):
            score += 15.0
            missing_tests = True
            reasons.append("No unit or integration test updates included with code changes")

        # Cap score at 100
        score = min(100.0, score)

        # Determine level
        if score >= 75.0:
            level = "CRITICAL"
        elif score >= 50.0:
            level = "HIGH"
        elif score >= 25.0:
            level = "MEDIUM"
        else:
            level = "LOW"

        if not reasons:
            reasons.append("Low risk: Isolated changes with existing test coverage.")

        return RiskReport(
            risk_score=round(score, 1),
            risk_level=level,
            reasons=reasons,
            affected_dependents_count=dependents_count,
            missing_tests=missing_tests
        )
