"""
Idempotency & Safe Retry Protection Module
Prevents duplicate branch creation, duplicate file commits, or duplicate PR creation by verifying live repository state.
"""
from typing import Dict, Any, List, Optional
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer


class IdempotencyGuard:
    """
    Guards GitHub write mutations against duplicate execution.
    """

    def __init__(self, mcp_tools: GitHubMCPTools):
        self.mcp = mcp_tools

    def safe_create_branch(self, repo_name: str, branch_name: str, base_branch: str = "main") -> Dict[str, Any]:
        """Verify branch existence before attempting creation."""
        try:
            # Check if branch ref already exists
            endpoint = f"/repos/{repo_name}/git/ref/heads/{branch_name}"
            existing = self.mcp._api_get(endpoint)
            return {
                "branch": branch_name,
                "status": "already_exists",
                "sha": existing.get("object", {}).get("sha")
            }
        except Exception:
            # Branch does not exist, proceed with creation
            return self.mcp.create_branch(repo_name, branch_name, base_branch=base_branch)

    def safe_create_pull_request(self, repo_name: str, title: str, body: str, head: str, base: str = "main") -> Dict[str, Any]:
        """Search for existing PR with identical head and base before creating a new PR."""
        try:
            existing_prs = self.mcp.list_pull_requests(repo_name, state="open")
            for pr in existing_prs:
                if pr.get("head") == head and pr.get("base") == base:
                    return {
                        "number": pr.get("number"),
                        "title": pr.get("title"),
                        "html_url": f"https://github.com/{repo_name}/pull/{pr.get('number')}",
                        "status": "already_exists"
                    }
        except Exception:
            pass

        # No duplicate PR found, proceed to create PR
        return self.mcp.create_pull_request(repo_name, title, body, head, base)
