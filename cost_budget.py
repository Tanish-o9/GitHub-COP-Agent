"""
Cost & Resource Budget Manager
Tracks and enforces execution limits for agent steps, MCP tool calls, RAG chunks, and duration.
"""
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Default Budget Limits
DEFAULT_MAX_AGENT_CALLS = 50
DEFAULT_MAX_MCP_CALLS = 100
DEFAULT_MAX_DURATION_SEC = 600.0  # 10 minutes
DEFAULT_MAX_RETRIEVED_CHUNKS = 200


class ResourceBudgetExceeded(Exception):
    """Raised when a workflow exceeds its configured resource budget."""
    pass


class ResourceBudgetTracker:
    """Tracks resource consumption for an active agent run."""

    def __init__(
        self,
        max_agent_calls: int = DEFAULT_MAX_AGENT_CALLS,
        max_mcp_calls: int = DEFAULT_MAX_MCP_CALLS,
        max_duration_sec: float = DEFAULT_MAX_DURATION_SEC,
        max_chunks: int = DEFAULT_MAX_RETRIEVED_CHUNKS
    ):
        self.max_agent_calls = max_agent_calls
        self.max_mcp_calls = max_mcp_calls
        self.max_duration_sec = max_duration_sec
        self.max_chunks = max_chunks

        self.start_time = time.time()
        self.agent_calls = 0
        self.mcp_calls = 0
        self.retrieved_chunks = 0
        self.files_read = 0

    def record_agent_call(self):
        """Record an agent execution step."""
        self.agent_calls += 1
        self.check_budget()

    def record_mcp_call(self):
        """Record an MCP tool invocation."""
        self.mcp_calls += 1
        self.check_budget()

    def record_chunks_retrieved(self, count: int):
        """Record RAG chunks fetched."""
        self.retrieved_chunks += count
        self.check_budget()

    def record_file_read(self):
        """Record file read operation."""
        self.files_read += 1

    def elapsed_time(self) -> float:
        """Calculate elapsed seconds."""
        return time.time() - self.start_time

    def check_budget(self):
        """Verify consumption against configured limits."""
        elapsed = self.elapsed_time()

        if self.agent_calls > self.max_agent_calls:
            raise ResourceBudgetExceeded(
                f"Workflow stopped because the configured resource budget was reached: "
                f"Agent calls ({self.agent_calls}/{self.max_agent_calls})."
            )
        if self.mcp_calls > self.max_mcp_calls:
            raise ResourceBudgetExceeded(
                f"Workflow stopped because the configured resource budget was reached: "
                f"MCP calls ({self.mcp_calls}/{self.max_mcp_calls})."
            )
        if elapsed > self.max_duration_sec:
            raise ResourceBudgetExceeded(
                f"Workflow stopped because the configured resource budget was reached: "
                f"Workflow duration ({elapsed:.1f}s/{self.max_duration_sec}s)."
            )
        if self.retrieved_chunks > self.max_chunks:
            raise ResourceBudgetExceeded(
                f"Workflow stopped because the configured resource budget was reached: "
                f"Retrieved chunks ({self.retrieved_chunks}/{self.max_chunks})."
            )

    def get_summary(self) -> Dict[str, Any]:
        """Fetch resource usage metrics summary."""
        return {
            "agent_calls": self.agent_calls,
            "mcp_calls": self.mcp_calls,
            "retrieved_chunks": self.retrieved_chunks,
            "files_read": self.files_read,
            "elapsed_sec": round(self.elapsed_time(), 2),
            "limits": {
                "max_agent_calls": self.max_agent_calls,
                "max_mcp_calls": self.max_mcp_calls,
                "max_duration_sec": self.max_duration_sec,
                "max_chunks": self.max_chunks
            }
        }
