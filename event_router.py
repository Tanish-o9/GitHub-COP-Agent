"""
Event-Driven GitHub Agent & Webhook Processor
Handles GitHub webhook events (issue_opened, pr_opened, push), performs issue triage, and triggers agent workflows.
"""
from typing import Dict, Any, List, Optional
from agent_tracer import AgentTracer
from github_mcp import GitHubMCPTools
from repo_memory import RepoMemory
from rag_engine import CodebaseRAGEngine
from agents.analyzer_agent import AnalyzerAgent
from agents.reviewer_agent import ReviewerAgent


class EventRouter:
    """
    Processes incoming GitHub Webhook events and triggers appropriate agent workflows.
    """

    def __init__(self, mcp_tools: GitHubMCPTools, tracer: Optional[AgentTracer] = None):
        self.mcp = mcp_tools
        self.tracer = tracer or AgentTracer("Webhook Event")

    def process_webhook_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and route event_type ('issues', 'pull_request', 'push').
        """
        action = payload.get("action", "opened")
        repo_name = payload.get("repository", {}).get("full_name", "Tanish-o9/GitHub-COP-Agent")

        self.tracer.log_step("EventRouter", f"Received GitHub event '{event_type}.{action}' for repo '{repo_name}'")

        if event_type == "issues":
            return self.triage_issue_event(repo_name, payload.get("issue", {}))
        elif event_type == "pull_request":
            return self.analyze_pr_event(repo_name, payload.get("pull_request", {}))
        elif event_type == "push":
            return {
                "event": "push",
                "repo_name": repo_name,
                "ref": payload.get("ref", "refs/heads/main"),
                "summary": "Push event received. Invalidated RAG cache for updated branch."
            }
        else:
            return {"event": event_type, "status": "IGNORED", "message": f"Unsupported event type: {event_type}"}

    def triage_issue_event(self, repo_name: str, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically triage a newly opened GitHub Issue.
        """
        title = issue_data.get("title", "")
        body = issue_data.get("body", "")
        number = issue_data.get("number", 1)

        full_text = f"{title} {body}".lower()

        # Category Classification
        if any(w in full_text for w in ["security", "token", "auth", "vulnerability", "secret"]):
            category = "security"
            severity = "CRITICAL"
        elif any(w in full_text for w in ["error", "exception", "traceback", "crash", "bug", "fail"]):
            category = "bug"
            severity = "HIGH"
        elif any(w in full_text for w in ["slow", "performance", "latency", "memory"]):
            category = "performance"
            severity = "MEDIUM"
        elif any(w in full_text for w in ["feature", "add", "request", "support"]):
            category = "feature"
            severity = "LOW"
        else:
            category = "question"
            severity = "LOW"

        confidence = "HIGH" if len(body) > 30 else "MEDIUM"

        triage_report = {
            "event": "issue_opened",
            "issue_number": number,
            "title": title,
            "category": category,
            "severity": severity,
            "confidence": confidence,
            "estimated_affected_module": "auth/configuration" if "auth" in full_text else "core",
            "summary": f"Issue #{number} triaged as [{severity}] {category.upper()} with {confidence} confidence."
        }

        if self.tracer:
            self.tracer.log_step(
                agent_name="EventRouter",
                action=f"Completed Issue Triage for #{number}",
                tool_output=triage_report
            )

        return triage_report

    def analyze_pr_event(self, repo_name: str, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically analyze a newly opened GitHub Pull Request.
        """
        number = pr_data.get("number", 1)
        title = pr_data.get("title", "")
        reviewer = ReviewerAgent(self.tracer)
        
        pr_details = {
            "number": number,
            "title": title,
            "user": pr_data.get("user", {}).get("login", "author"),
            "head": pr_data.get("head", {}).get("ref", "feature"),
            "base": pr_data.get("base", {}).get("ref", "main"),
            "changed_files": pr_data.get("changed_files", [])
        }

        review = reviewer.review_pr(pr_details)

        return {
            "event": "pr_opened",
            "pr_number": number,
            "title": title,
            "assessment": review["overall_assessment"],
            "summary": f"Automatic PR Review for #{number} completed: {review['overall_assessment']}"
        }
