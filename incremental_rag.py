"""
Incremental RAG Indexer
Processes push webhooks to incrementally update vector/chunk index for modified repository files.
"""
import time
import logging
from typing import List, Dict, Any, Optional
from rag_engine import CodebaseRAGEngine, CodeChunk
from cache_manager import CacheManager
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer

logger = logging.getLogger(__name__)


class IncrementalRAGIndexer:
    """Handles partial/incremental re-indexing of modified files on push events."""

    def __init__(self, rag_engine: CodebaseRAGEngine, cache_manager: Optional[CacheManager] = None):
        self.rag_engine = rag_engine
        self.cache_manager = cache_manager or CacheManager()

    def update_modified_files(
        self,
        mcp_tools: GitHubMCPTools,
        modified_files: List[str],
        removed_files: List[str] = None
    ) -> Dict[str, Any]:
        """
        Incrementally re-indexes only the files changed in a commit/push.
        """
        removed_files = removed_files or []
        start_time = time.time()

        # 1. Purge chunks belonging to modified or removed files
        files_to_purge = set(modified_files).union(set(removed_files))
        original_count = len(self.rag_engine.chunks)
        
        self.rag_engine.chunks = [
            chunk for chunk in self.rag_engine.chunks
            if chunk.file_path not in files_to_purge
        ]
        purged_count = original_count - len(self.rag_engine.chunks)

        # 2. Re-index modified files
        reindexed_count = 0
        added_chunks = 0

        for path in modified_files:
            if not self.rag_engine.is_indexable(path):
                continue
            try:
                fc = mcp_tools.get_file_content(self.rag_engine.repo_name, path, ref=self.rag_engine.branch)
                content = fc.get("content", "")
                sanitized_content = AgentTracer.sanitize_secrets(content)
                new_chunks = self.rag_engine.chunk_code_file(path, sanitized_content)
                self.rag_engine.chunks.extend(new_chunks)
                reindexed_count += 1
                added_chunks += len(new_chunks)
            except Exception as e:
                logger.warning(f"[IncrementalRAG] Failed to index modified file {path}: {e}")

        # 3. Invalidate repository cache
        self.cache_manager.invalidate_repo(self.rag_engine.repo_name)

        duration = round(time.time() - start_time, 3)
        summary = {
            "repository": self.rag_engine.repo_name,
            "branch": self.rag_engine.branch,
            "modified_files": modified_files,
            "removed_files": removed_files,
            "purged_chunks": purged_count,
            "added_chunks": added_chunks,
            "total_chunks": len(self.rag_engine.chunks),
            "duration_sec": duration,
            "status": "COMPLETED"
        }
        logger.info(f"[IncrementalRAG] Completed incremental update for {self.rag_engine.repo_name}: {summary}")
        return summary
