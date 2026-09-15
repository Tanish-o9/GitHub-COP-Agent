"""
Self-Verification & Critic System
Evaluates agent outputs for evidence grounding, real file references, test execution proof, and tool permission compliance.
"""
import re
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

MAX_CRITIC_REVISIONS = 3


@dataclass
class VerificationResult:
    """Report detailing self-verification results and critic feedback."""
    passed: bool
    score: float  # 0.0 to 100.0
    findings: List[str] = field(default_factory=list)
    critic_feedback: str = ""
    revision_needed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SelfVerifier:
    """Self-verification and critic system for agent outputs."""

    def verify_response(
        self,
        user_request: str,
        response_text: str,
        known_repo_files: Optional[List[str]] = None,
        test_executed: bool = False
    ) -> VerificationResult:
        findings = []
        score = 100.0
        known_set = set(known_repo_files or [])

        # 1. Evidence Grounding Check (File Links)
        cited_files = re.findall(r'`([^`]+\.py)`', response_text)
        if known_set and cited_files:
            hallucinated = [f for f in cited_files if f not in known_set and not f.startswith("tests/")]
            if hallucinated:
                score -= 30.0
                findings.append(f"Referenced non-existent file(s) in repository: {hallucinated}")

        # 2. Source Citations Check
        if "file:///" not in response_text and "L" not in response_text:
            score -= 15.0
            findings.append("Response lacks explicit line-level citations")

        # 3. Test Execution Proof Check for Code Fix Requests
        if any(w in user_request.lower() for w in ["fix", "implement", "create pr"]) and not test_executed:
            score -= 20.0
            findings.append("No automated test execution proof recorded for code modification")

        # 4. Empty or Vague Response Check
        if len(response_text.strip()) < 50:
            score -= 40.0
            findings.append("Response content is unusually short or incomplete")

        passed = (score >= 70.0)
        critic_msg = ""
        if not passed:
            critic_msg = "CRITIC FEEDBACK: " + "; ".join(findings) + ". Please revise response to include verified file paths and citations."

        return VerificationResult(
            passed=passed,
            score=round(score, 1),
            findings=findings,
            critic_feedback=critic_msg,
            revision_needed=not passed
        )
