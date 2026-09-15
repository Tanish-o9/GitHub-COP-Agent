"""
Prompt Injection Defense Module
Sanitizes untrusted repository content (READMEs, issue bodies, PR comments) to prevent malicious instruction hijacking.
"""
import re
from typing import Dict, Any, List, Optional


class PromptInjectionGuard:
    """
    Enforces trust boundaries between system instructions, user commands, and untrusted repository data.
    """

    INJECTION_PATTERNS = [
        r'ignore\s+(all\s+)?previous\s+instructions',
        r'disregard\s+system\s+prompts',
        r'expose\s+the\s+(github_token|api_key|password|secret)',
        r'override\s+tool\s+policy',
        r'bypass\s+human\s+approval',
        r'delete\s+all\s+branches',
        r'force\s+push\s+to\s+main'
    ]

    @classmethod
    def sanitize_untrusted_content(cls, raw_content: str) -> str:
        """
        Neutralize prompt injection attempts inside untrusted repository text.
        """
        if not isinstance(raw_content, str):
            return raw_content

        sanitized = raw_content
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, sanitized, flags=re.IGNORECASE):
                sanitized = re.sub(
                    pattern,
                    '[UNTRUSTED_CONTENT_FILTERED_INJECTION_ATTEMPT]',
                    sanitized,
                    flags=re.IGNORECASE
                )

        return sanitized

    @classmethod
    def wrap_as_data_boundary(cls, content_label: str, content: str) -> str:
        """
        Wrap untrusted content in explicit XML tags declaring it as data.
        """
        clean_data = cls.sanitize_untrusted_content(content)
        return (
            f"<{content_label}_UNTRUSTED_DATA>\n"
            f"{clean_data}\n"
            f"</{content_label}_UNTRUSTED_DATA>"
        )
