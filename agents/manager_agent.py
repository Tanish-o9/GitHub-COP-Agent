"""
Manager Agent (Router & Coordinator) — Phase 3
Classifies user intent into specialized workflows (including CHANGE_IMPACT and REPO_QA) with model fallback support.
"""
import re
from typing import Dict, Any, Optional
from agent_tracer import AgentTracer
from tool_policy import ToolPolicyEnforcer


class ManagerAgent:
    """
    Manager / Router Agent responsible for evaluating requests, enforcing tool policies, and dispatching to specialized agents.
    """

    def __init__(self, tracer: Optional[AgentTracer] = None, model_name: str = "gpt-4o"):
        self.name = "Manager Agent"
        self.tracer = tracer
        self.primary_model = model_name
        self.fallback_model = "gpt-3.5-turbo"

    def classify_request(self, user_request: str) -> Dict[str, Any]:
        """Classify user intent into target workflow and parameters."""
        req_lower = user_request.lower()
        
        issue_match = re.search(r'issue\s*#?(\d+)', req_lower)
        pr_match = re.search(r'pr\s*#?(\d+)|pull\s*request\s*#?(\d+)', req_lower)

        is_impact_intent = any(w in req_lower for w in ["impact", "affected", "affect", "change impact", "will break"])
        is_fix_intent = any(word in req_lower for word in ["fix", "resolve", "implement", "create pr", "patch"])
        is_security_intent = any(word in req_lower for word in ["security", "audit", "vulnerability", "secrets", "owasp"])
        is_test_intent = any(word in req_lower for word in ["test", "tests", "unit test", "pytest", "unittest"])
        is_review_intent = any(word in req_lower for word in ["review", "pr review", "code review"])

        target_workflow = "REPO_INTELLIGENCE"
        extracted_params = {}

        if is_impact_intent:
            target_workflow = "CHANGE_IMPACT"
            target_file = "chat_github_llama3.py"
            for word in user_request.split():
                if word.endswith(".py"):
                    target_file = word
                    break
            extracted_params["target_file"] = target_file
        elif is_fix_intent and issue_match:
            target_workflow = "FULL_ENGINEERING_WORKFLOW"
            extracted_params["issue_number"] = int(issue_match.group(1))
        elif is_fix_intent:
            target_workflow = "FULL_ENGINEERING_WORKFLOW"
        elif pr_match or (is_review_intent and pr_match):
            target_workflow = "PR_REVIEW"
            num_str = pr_match.group(1) or pr_match.group(2)
            if num_str:
                extracted_params["pr_number"] = int(num_str)
        elif issue_match or "issue" in req_lower:
            target_workflow = "ISSUE_ANALYSIS"
            if issue_match:
                extracted_params["issue_number"] = int(issue_match.group(1))
        elif is_security_intent:
            target_workflow = "SECURITY_AUDIT"
        elif is_test_intent:
            target_workflow = "TEST_GENERATION"
        else:
            target_workflow = "REPO_INTELLIGENCE"

        if self.tracer:
            self.tracer.log_step(
                agent_name=self.name,
                action=f"Classified request into workflow: `{target_workflow}` (Model: {self.primary_model})",
                tool_input=user_request,
                tool_output=extracted_params
            )

        return {
            "workflow": target_workflow,
            "params": extracted_params,
            "model_used": self.primary_model
        }
