"""
Patch Scope Optimizer
Analyzes proposed patches for unnecessary scope inflation and enforces minimal safe patch discipline.
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
from semantic_diff import ChangeSummary

logger = logging.getLogger(__name__)


@dataclass
class PatchScopeReport:
    """Report evaluating patch scope discipline and minimality."""
    scope_score: float  # 0.0 to 100.0 (100 = perfectly focused minimal patch)
    is_minimal: bool
    unrelated_changes: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PatchOptimizer:
    """Evaluates proposed patches for minimality and scope discipline."""

    def evaluate_scope(self, change_summary: ChangeSummary) -> PatchScopeReport:
        score = 100.0
        unrelated = []
        recs = []

        files_count = len(change_summary.files_changed)
        if files_count > 5:
            score -= 30.0
            unrelated.append(f"PR touches {files_count} files (exceeds recommended target of <=3 files)")
            recs.append("Restrict changes to target module and corresponding test file")

        # Check for un-targeted doc/config edits
        for f in change_summary.files_changed:
            if any(ext in f for ext in [".md", ".txt", ".yml", ".json"]) and not any(p in f for p in ["src/", "api/", "tests/"]):
                score -= 10.0
                unrelated.append(f"Non-code configuration file modified: {f}")

        is_minimal = (score >= 70.0)
        if not recs:
            recs.append("Patch scope is well-disciplined and minimal.")

        return PatchScopeReport(
            scope_score=max(0.0, score),
            is_minimal=is_minimal,
            unrelated_changes=unrelated,
            recommendations=recs
        )
