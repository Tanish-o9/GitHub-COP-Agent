"""
Test Impact & Coverage Intelligence
Identifies related test suites, affected downstream tests, and missing test coverage areas for proposed changes.
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from code_graph import CodeIntelligenceGraph

logger = logging.getLogger(__name__)


@dataclass
class TestImpactReport:
    """Report detailing affected test suites and recommended test generation targets."""
    target_files: List[str] = field(default_factory=list)
    related_tests: List[str] = field(default_factory=list)
    affected_tests: List[str] = field(default_factory=list)
    missing_coverage_areas: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TestImpactAnalyzer:
    """Analyzes test relationships and predicts test coverage requirements."""

    def analyze_impact(
        self,
        changed_files: List[str],
        code_graph: Optional[CodeIntelligenceGraph] = None
    ) -> TestImpactReport:
        report = TestImpactReport(target_files=changed_files)
        related_tests_set = set()
        missing_areas = []
        recs = []

        for file_path in changed_files:
            # Conventions check: test_<basename>.py
            basename = file_path.split("/")[-1].replace(".py", "")
            convention_test = f"tests/test_{basename}.py"
            related_tests_set.add(convention_test)

            if code_graph:
                graph_tests = code_graph.get_related_tests(file_path)
                for gt in graph_tests:
                    related_tests_set.add(gt.file_path)

            if "auth" in file_path or "security" in file_path:
                missing_areas.append(f"Security edge cases for {file_path} (unauthorized / invalid token)")
                recs.append(f"Generate unit tests for security boundary handling in {file_path}")

            if "api/" in file_path:
                missing_areas.append(f"HTTP status response tests for {file_path} (400 Bad Request, 404 Not Found)")
                recs.append(f"Run API integration suite for {file_path}")

        report.related_tests = list(related_tests_set)
        report.affected_tests = list(related_tests_set)
        report.missing_coverage_areas = missing_areas
        if not recs:
            recs.append(f"Execute pytest across related test suites: {', '.join(report.related_tests[:3])}")
        report.recommendations = recs

        return report
