"""
Merge Conflict Intelligence Engine
Analyzes Git merge conflicts, identifies conflicting symbols, and proposes safe resolutions.
Never automatically resolves high-risk security/auth/db conflicts without human approval.
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class ConflictAnalysisReport:
    """Report detailing detected merge conflicts and recommended resolution strategy."""
    conflicting_files: List[str] = field(default_factory=list)
    conflicting_symbols: List[str] = field(default_factory=list)
    is_high_risk: bool = False
    proposed_resolution: str = ""
    requires_human_approval: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MergeConflictAnalyzer:
    """Analyzes merge conflict markers and proposes resolutions."""

    def analyze_conflict(self, conflict_text: str, file_path: str = "src/main.py") -> ConflictAnalysisReport:
        conflicting_symbols = []
        is_high_risk = False

        if any(k in file_path.lower() for k in ["auth", "security", "database", "model", "migration"]):
            is_high_risk = True

        for line in conflict_text.splitlines():
            if line.startswith("+def ") or line.startswith("<<<<<<<") or line.startswith(">>>>>>>"):
                if "def " in line:
                    sym = line.split("(")[0].replace("def ", "").strip()
                    conflicting_symbols.append(sym)

        resolution = f"Combine incoming fix with base branch changes in `{file_path}`"
        if is_high_risk:
            resolution = f"CRITICAL: High-risk security/db conflict in `{file_path}`. Human approval mandatory."

        return ConflictAnalysisReport(
            conflicting_files=[file_path],
            conflicting_symbols=conflicting_symbols,
            is_high_risk=is_high_risk,
            proposed_resolution=resolution,
            requires_human_approval=True  # Always require approval for merge conflicts!
        )
