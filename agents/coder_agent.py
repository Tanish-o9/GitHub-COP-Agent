"""
Coder Agent
Generates implementation plans, proposed code modifications, patches, and handles review revision feedback.
"""
from typing import Dict, Any, List, Optional
from agent_tracer import AgentTracer


class CoderAgent:
    """
    Code generation, plan formulation, and revision feedback handling agent.
    """

    def __init__(self, tracer: Optional[AgentTracer] = None):
        self.name = "Coder Agent"
        self.tracer = tracer

    def generate_implementation_plan(
        self,
        issue_title: str,
        target_path: str,
        root_cause: str
    ) -> List[str]:
        """Formulate a step-by-step implementation plan prior to modifying code."""
        plan_steps = [
            f"Inspect `{target_path}` and target module functions.",
            "Locate unhandled exception path or token loading flaw.",
            f"Update `{target_path}` to safely read configuration from `os.getenv('GITHUB_TOKEN')`.",
            "Add safety input validation and fallback default handling.",
            "Generate regression unit test suite covering happy path and edge cases.",
            "Run automated test runner and verify execution results.",
            "Audit diff with Reviewer Agent and Security Gate.",
            "Request explicit human approval before pushing branch or creating PR."
        ]

        if self.tracer:
            self.tracer.log_step(
                agent_name=self.name,
                action=f"Formulated Implementation Plan ({len(plan_steps)} steps)",
                tool_output=plan_steps
            )

        return plan_steps

    def propose_fix(
        self,
        target_file: str,
        original_content: str,
        fix_description: str,
        revision_feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """Formulate code fix and generate modified content, taking revision feedback into account."""
        modified_content = original_content

        # Apply target refactoring
        if "os.getenv(\"Your GitHub Token\")" in original_content:
            modified_content = original_content.replace(
                'os.getenv("Your GitHub Token")',
                'os.getenv("GITHUB_TOKEN")'
            )
        elif "token\":\"Your GitHub Token\"" in original_content:
            modified_content = original_content.replace(
                '"token":"Your GitHub Token"',
                '"token": os.getenv("GITHUB_TOKEN", "")'
            )

        # Incorporate revision feedback if revising
        if revision_feedback:
            modified_content = f"# Revision applied: {revision_feedback}\n" + modified_content

        patch_plan = {
            "target_file": target_file,
            "fix_description": fix_description,
            "original_content": original_content,
            "modified_content": modified_content,
            "revision_feedback": revision_feedback,
            "lines_changed": abs(len(modified_content.splitlines()) - len(original_content.splitlines())) + 1
        }

        if self.tracer:
            self.tracer.log_step(
                agent_name=self.name,
                action=f"Generated patch for `{target_file}`" + (f" (Revision)" if revision_feedback else ""),
                tool_output=patch_plan
            )

        return patch_plan
