"""
Semantic Git Diff Analyzer
Parses raw diffs or file change maps to extract symbol-level changes, API modifications, schema edits, and risk indicators.
"""
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class ChangeSummary:
    """Structured summary of semantic code changes extracted from a diff."""
    files_changed: List[str] = field(default_factory=list)
    added_symbols: List[str] = field(default_factory=list)
    removed_symbols: List[str] = field(default_factory=list)
    modified_symbols: List[str] = field(default_factory=list)
    behavior_changes: List[str] = field(default_factory=list)
    api_changes: List[str] = field(default_factory=list)
    schema_changes: List[str] = field(default_factory=list)
    test_changes: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SemanticDiffAnalyzer:
    """Analyzes code diffs to determine symbol modifications and architectural impact."""

    def analyze_diff(self, diff_text: str, changed_files: Optional[List[str]] = None) -> ChangeSummary:
        summary = ChangeSummary()
        summary.files_changed = changed_files or []

        if not diff_text:
            return summary

        lines = diff_text.splitlines()
        current_file = ""

        for line in lines:
            if line.startswith("+++ b/"):
                current_file = line[6:]
                if current_file not in summary.files_changed:
                    summary.files_changed.append(current_file)
            elif line.startswith("+def ") or line.startswith("+class "):
                sym = line.split("(")[0].replace("+def ", "").replace("+class ", "").strip()
                summary.added_symbols.append(sym)
                if "test" in current_file:
                    summary.test_changes.append(f"Added test entity '{sym}'")
            elif line.startswith("-def ") or line.startswith("-class "):
                sym = line.split("(")[0].replace("-def ", "").replace("-class ", "").strip()
                summary.removed_symbols.append(sym)
                summary.risk_factors.append(f"Removed symbol '{sym}' from {current_file}")
            elif line.startswith("+") and not line.startswith("+++"):
                # Detect security/auth or model modifications
                if any(k in line.lower() for k in ["token", "password", "jwt", "auth", "secret", "session"]):
                    if "Authentication logic modified" not in summary.behavior_changes:
                        summary.behavior_changes.append("Authentication/Security logic modified")
                        summary.risk_factors.append("Security sensitive token/auth handling changed")
                if "class " in line and "Base" in line:
                    summary.schema_changes.append(f"Database model modified in {current_file}")

        # Classify risk factors based on scope
        if len(summary.files_changed) > 5:
            summary.risk_factors.append(f"Broad change scope spanning {len(summary.files_changed)} files")
        if not summary.test_changes and any("src/" in f for f in summary.files_changed):
            summary.risk_factors.append("Source code modified without corresponding test modifications")

        return summary
