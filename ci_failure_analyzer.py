"""
CI Failure Analyzer
Parses CI test failure output, stack traces, and exception logs to pinpoint failing files, symbols, and line numbers.
"""
import re
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ParsedCIFailure:
    """Structured representation of a parsed CI test failure."""
    failing_test: str
    error_message: str
    target_file: str
    line_number: int
    stack_trace: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CIFailureAnalyzer:
    """Parses exception stack traces and CI test logs."""

    def parse_failure(self, ci_log: str) -> ParsedCIFailure:
        failing_test = "unknown_test"
        error_msg = "CI Test Failure"
        target_file = ""
        line_num = 1
        stack = []

        lines = ci_log.splitlines()
        for i, line in enumerate(lines):
            if "FAIL:" in line or "FAILED" in line or "ERROR:" in line:
                failing_test = line.strip()
            if "AssertionError" in line or "KeyError" in line or "TypeError" in line or "ValueError" in line:
                error_msg = line.strip()
            if 'File "' in line and '.py"' in line:
                match = re.search(r'File "([^"]+)", line (\d+)', line)
                if match:
                    target_file = match.group(1)
                    line_num = int(match.group(2))
                    stack.append(line.strip())

        return ParsedCIFailure(
            failing_test=failing_test,
            error_message=error_msg,
            target_file=target_file,
            line_number=line_num,
            stack_trace=stack
        )
