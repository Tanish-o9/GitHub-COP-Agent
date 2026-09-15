"""
Evidence & Hallucination Guard Module
Validates agent response claims against retrieved repository context to detect fictitious files, nonexistent symbols, or unsupported claims.
"""
import re
from typing import Dict, Any, List, Optional
from agent_tracer import AgentTracer


class EvidenceChecker:
    """
    Validation layer checking factual claims against actual repository evidence.
    """

    @staticmethod
    def validate_response(
        response_text: str,
        retrieved_files: List[Dict[str, Any]],
        known_tree_paths: List[str]
    ) -> Dict[str, Any]:
        """
        Scan response text for referenced file paths and verify their existence in repository.
        """
        # Extract file paths mentioned in text (e.g. `src/auth.py` or filename.ext)
        mentioned_files = re.findall(r'[`\'"]([A-Za-z0-9_\-/\\]+\.[A-Za-z0-9]+)[`\'"]', response_text)
        
        valid_paths = set(known_tree_paths + [f.get("path", "") for f in retrieved_files])
        
        hallucinated_files = []
        verified_files = []

        for f in set(mentioned_files):
            # Ignore standard markdown/system files
            if f in ["README.md", "requirements.txt", "package.json"]:
                verified_files.append(f)
                continue

            if any(f in path or path.endswith(f) for path in valid_paths):
                verified_files.append(f)
            else:
                hallucinated_files.append(f)

        if not hallucinated_files and verified_files:
            classification = "SUPPORTED"
        elif verified_files and hallucinated_files:
            classification = "PARTIALLY_SUPPORTED"
        else:
            classification = "UNSUPPORTED"

        sanitized_response = response_text
        if hallucinated_files:
            warning_note = f"\n\n> ⚠️ *Note: The following referenced paths could not be verified in the active repository tree*: `{', '.join(hallucinated_files)}`"
            sanitized_response += warning_note

        return {
            "classification": classification,
            "verified_files": verified_files,
            "hallucinated_files": hallucinated_files,
            "sanitized_response": sanitized_response
        }
