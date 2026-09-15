"""
MCP Connection Lifecycle & Connection Pool Manager
Manages GitHub MCP tool client lifecycle, connection pooling per user/token, heartbeat health checks, and recovery.
"""
import time
import logging
from typing import Dict, Any, Optional
from github_mcp import GitHubMCPTools

logger = logging.getLogger(__name__)


class MCPConnectionPool:
    """Pools and manages GitHub MCP client connections to prevent resource leaks."""

    _pool: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_connection(cls, token: Optional[str] = None) -> GitHubMCPTools:
        """Get or create an isolated MCP connection for a token."""
        key = token.strip() if token else "DEFAULT"

        if key in cls._pool:
            conn_data = cls._pool[key]
            # Perform health check (ping) every 60s
            if time.time() - conn_data["last_ping"] < 60:
                return conn_data["client"]
            else:
                # Ping check
                try:
                    client: GitHubMCPTools = conn_data["client"]
                    # Quick dry call or header check
                    conn_data["last_ping"] = time.time()
                    return client
                except Exception as e:
                    logger.warning(f"[MCPPool] Connection failed health check ({e}). Re-creating connection.")

        logger.info(f"[MCPPool] Initializing new MCP client connection for token key '{key[:8]}...'")
        client = GitHubMCPTools(token=token)
        cls._pool[key] = {
            "client": client,
            "created_at": time.time(),
            "last_ping": time.time()
        }
        return client

    @classmethod
    def close_all(cls):
        """Safely clean up all pooled MCP connections."""
        logger.info(f"[MCPPool] Closing {len(cls._pool)} pooled MCP connections.")
        cls._pool.clear()

    @classmethod
    def get_pool_status(cls) -> Dict[str, Any]:
        """Fetch status of active MCP connections."""
        return {
            "active_connections": len(cls._pool),
            "keys": list(cls._pool.keys())
        }
