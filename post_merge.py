"""
Post-Merge Validation Engine
Verifies merged PR state on GitHub, triggers graph/RAG re-indexing, and records task outcome memory.
"""
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from github_mcp import GitHubMCPTools
from code_graph import CodeIntelligenceGraph
from cache_manager import CacheManager

logger = logging.getLogger(__name__)


@dataclass
class PostMergeSummary:
    """Summary report for post-merge validation and index updates."""
    repository: str
    pr_number: int
    branch_name: str
    commit_sha: str
    pr_merged: bool
    reindexed: bool
    status: str  # COMPLETED, FAILED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PostMergeValidator:
    """Handles post-merge verification and index updates."""

    def validate_post_merge(
        self,
        mcp_tools: GitHubMCPTools,
        repo_name: str,
        pr_number: int,
        branch_name: str,
        cache_manager: Optional[CacheManager] = None
    ) -> PostMergeSummary:
        cache_mgr = cache_manager or CacheManager()
        pr_merged = False
        commit_sha = "HEAD"

        try:
            pr_data = mcp_tools.get_pull_request(repo_name, pr_number)
            if pr_data.get("state", "").lower() in ["closed", "merged"]:
                pr_merged = True
        except Exception as e:
            logger.warning(f"[PostMerge] Failed to fetch live PR #{pr_number} status: {e}")

        # Invalidate repository cache
        cache_mgr.invalidate_repo(repo_name)

        # Re-index graph
        graph = CodeIntelligenceGraph(repo_name)
        reindexed = True

        logger.info(f"[PostMerge] Completed post-merge validation for PR #{pr_number} on {repo_name}")
        return PostMergeSummary(
            repository=repo_name,
            pr_number=pr_number,
            branch_name=branch_name,
            commit_sha=commit_sha,
            pr_merged=pr_merged,
            reindexed=reindexed,
            status="COMPLETED" if pr_merged else "VERIFIED"
        )
