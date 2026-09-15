"""
Repository Context Cache Module
Caches read-only repository metadata and directory trees to prevent duplicate API tool calls.
"""
import time
from typing import Dict, Any, Optional
from agent_tracer import AgentTracer


class RepoCache:
    """
    In-memory cache with TTL expiration for repository read operations.
    """

    _cache_store: Dict[str, Dict[str, Any]] = {}
    DEFAULT_TTL_SEC = 300  # 5 minutes

    @classmethod
    def _make_key(cls, repo_name: str, key_type: str, branch: Optional[str] = None) -> str:
        clean_repo = repo_name.strip().lower()
        return f"{clean_repo}:{branch or 'default'}:{key_type}"

    @classmethod
    def get(cls, repo_name: str, key_type: str, branch: Optional[str] = None) -> Optional[Any]:
        """Retrieve cached payload if fresh."""
        key = cls._make_key(repo_name, key_type, branch)
        entry = cls._cache_store.get(key)
        if not entry:
            return None
        
        if time.time() - entry["timestamp"] > cls.DEFAULT_TTL_SEC:
            del cls._cache_store[key]
            return None

        return entry["data"]

    @classmethod
    def set(cls, repo_name: str, key_type: str, data: Any, branch: Optional[str] = None) -> None:
        """Store payload in cache after redacting secrets."""
        key = cls._make_key(repo_name, key_type, branch)
        sanitized_data = data
        if isinstance(data, str):
            sanitized_data = AgentTracer.sanitize_secrets(data)

        cls._cache_store[key] = {
            "timestamp": time.time(),
            "data": sanitized_data
        }

    @classmethod
    def clear(cls) -> None:
        """Clear all cached entries."""
        cls._cache_store.clear()
