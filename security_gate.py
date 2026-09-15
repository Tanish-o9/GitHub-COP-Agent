"""
Security Gate Checker
Pre-PR security auditor analyzing proposed patches for hardcoded credentials, unsafe evaluation, and OWASP risks.
"""
import re
from typing import Dict, Any, List, Optional
from agent_tracer import AgentTracer


class SecurityGate:
    """
    Automated security check enforcing security boundaries before Git mutations.
    """

    @staticmethod
    def audit_patch(
        target_path: str,
        modified_content: str
    ) -> Dict[str, Any]:
        """
        Audit modified code content for critical security flaws.
        """
        critical_findings = []
        high_findings = []
        warnings = []

        # 1. Hardcoded Token Strings / Keys
        if re.search(r'(ghp_[A-Za-z0-9_]{36,})', modified_content):
            critical_findings.append({
                "type": "HARDCODED_GITHUB_TOKEN",
                "file": target_path,
                "description": "Hardcoded GitHub Personal Access Token detected in modified code."
            })
        if re.search(r'(sk-[A-Za-z0-9]{20,})', modified_content):
            critical_findings.append({
                "type": "HARDCODED_OPENAI_KEY",
                "file": target_path,
                "description": "Hardcoded OpenAI Secret Key detected in modified code."
            })
        if "Your GitHub Token" in modified_content or "your-api-key" in modified_content.lower():
            high_findings.append({
                "type": "INVALID_ENV_VAR_PLACEHOLDER",
                "file": target_path,
                "description": "Placeholder string literal 'Your GitHub Token' passed to os.getenv()."
            })

        # 2. Dynamic Execution Risks
        if "eval(" in modified_content or "exec(" in modified_content:
            critical_findings.append({
                "type": "DYNAMIC_CODE_EXECUTION",
                "file": target_path,
                "description": "Unsafe `eval()` or `exec()` statement detected in implementation."
            })

        # 3. Plaintext Password Fields
        if "st.text_input(" in modified_content and "password" in modified_content.lower() and "type=\"password\"" not in modified_content:
            warnings.append({
                "type": "PLAINTEXT_SECRET_INPUT",
                "file": target_path,
                "description": "Streamlit input for password missing type='password' mask."
            })

        passed = len(critical_findings) == 0

        result = {
            "passed": passed,
            "status": "PASS" if passed else "SECURITY REVIEW FAILED",
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "warnings": warnings,
            "recommendations": [
                "Remove all hardcoded tokens and use standard environment variables.",
                "Ensure dynamic execution statements are replaced with static function maps."
            ]
        }

        return result
