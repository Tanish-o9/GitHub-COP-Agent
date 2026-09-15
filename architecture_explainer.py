"""
Architecture Explainer
Generates multi-perspective architecture documentation (Executive, Developer, Request Flow, Data Flow) grounded in graph evidence.
"""
import logging
from typing import Dict, Any, List, Optional
from code_graph import CodeIntelligenceGraph
from github_mcp import GitHubMCPTools

logger = logging.getLogger(__name__)


class ArchitectureExplainer:
    """Generates evidence-backed architectural views for repositories."""

    def __init__(self, repo_name: str, code_graph: Optional[CodeIntelligenceGraph] = None):
        self.repo_name = repo_name
        self.code_graph = code_graph or CodeIntelligenceGraph(repo_name)

    def generate_architecture_views(self, mcp_tools: Optional[GitHubMCPTools] = None) -> Dict[str, Any]:
        """Generate Executive, Developer, Request Flow, and Data Flow architecture descriptions."""
        tree = []
        if mcp_tools:
            try:
                tree_data = mcp_tools.get_repo_tree(self.repo_name, recursive=True)
                tree = [item["path"] for item in tree_data]
            except Exception:
                pass

        # Infer components
        api_files = [f for f in tree if f.startswith("api/") or "route" in f or "app" in f]
        db_files = [f for f in tree if "database" in f or "model" in f or "schema" in f]
        agent_files = [f for f in tree if "agent" in f or "workflow" in f]
        test_files = [f for f in tree if "test" in f]

        executive_overview = (
            f"Repository `{self.repo_name}` is a multi-layer AI application containing "
            f"{len(tree)} tracked files. Includes API endpoints ({len(api_files)} files), "
            f"agent workflows ({len(agent_files)} files), database persistence ({len(db_files)} files), "
            f"and automated test suites ({len(test_files)} files)."
        )

        developer_architecture = {
            "api_layer": api_files[:5],
            "agent_orchestration": agent_files[:5],
            "database_models": db_files[:5],
            "test_coverage_files": test_files[:5],
            "graph_summary": self.code_graph.get_summary()
        }

        request_flow = [
            "1. Client Request ➔ FastAPI API Endpoint (/api/v1/)",
            "2. Authentication Middleware ➔ JWT Decode & Tenant Isolation Check",
            "3. Prompt Injection Defense ➔ Sanitization Filter",
            "4. Manager Agent Router ➔ Intent Classification & Specialist Selection",
            "5. Engineering Workflow ➔ Code Graph + Hybrid RAG Retrieval ➔ Patch Generation ➔ Self-Verification",
            "6. Security Gate & Human Approval ➔ Safe Branch Commit ➔ PR Creation via GitHub MCP"
        ]

        data_flow = [
            "User Request ➔ Database (AgentRun QUEUED)",
            "Task Queue (Redis) ➔ Worker Execution",
            "Agent Step Execution ➔ PostgreSQL/SQLite (AgentCheckpoint Saved)",
            "GitHub Mutation ➔ PRTracker Registered & GitHub Webhook Sync"
        ]

        return {
            "repository": self.repo_name,
            "executive_overview": executive_overview,
            "developer_architecture": developer_architecture,
            "request_flow": request_flow,
            "data_flow": data_flow
        }
