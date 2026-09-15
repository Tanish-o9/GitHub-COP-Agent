"""
Agent Observability & Nested Tracing Module — Phase 3
Tracks hierarchical agent executions, tool invocations, retries, efficiency metrics, and secret redaction.
"""
import re
import time
import uuid
from typing import Dict, Any, List, Optional


class AgentTracer:
    """
    Nested observability and efficiency metric tracking engine.
    """

    def __init__(self, request: str):
        self.run_id = f"RUN-{uuid.uuid4().hex[:6].upper()}"
        self.user_request = self.sanitize_secrets(request)
        self.start_time = time.time()
        self.steps: List[Dict[str, Any]] = []
        self.status = "RUNNING"
        
        # Efficiency Metrics
        self.tool_calls_count = 0
        self.agent_calls_count = 0
        self.files_read_count = 0
        self.retrieved_chunks_count = 0
        self.revision_cycles_count = 0
        self.test_execution_time = 0.0
        self.errors: List[str] = []

    @staticmethod
    def sanitize_secrets(text: str) -> str:
        """Redact sensitive credentials, tokens, and authorization headers."""
        if not isinstance(text, str):
            return text
        
        sanitized = re.sub(r'(ghp_[A-Za-z0-9_]{36,})', '[REDACTED_GITHUB_TOKEN]', text)
        sanitized = re.sub(r'(github_pat_[A-Za-z0-9_]{22,})', '[REDACTED_GITHUB_PAT]', text)
        sanitized = re.sub(r'(sk-[A-Za-z0-9]{20,})', '[REDACTED_OPENAI_KEY]', text)
        sanitized = re.sub(r'(Bearer\s+[A-Za-z0-9_\-\.]{20,})', 'Bearer [REDACTED]', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'(password["\']?\s*[:=]\s*["\']?[^"\'\s]+)', 'password="[REDACTED]"', sanitized, flags=re.IGNORECASE)
        return sanitized

    def log_step(
        self,
        agent_name: str,
        action: str,
        parent_agent: Optional[str] = "Manager Agent",
        tool_name: Optional[str] = None,
        tool_input: Optional[Any] = None,
        tool_output: Optional[Any] = None,
        duration: Optional[float] = None,
        retries: int = 0,
        error: Optional[str] = None
    ) -> None:
        """Record a nested agent step with metrics."""
        self.agent_calls_count += 1
        if tool_name:
            self.tool_calls_count += 1
            if tool_name in ["get_file_content", "search_code"]:
                self.files_read_count += 1

        sanitized_input = self.sanitize_secrets(str(tool_input)) if tool_input else None
        sanitized_output = self.sanitize_secrets(str(tool_output)) if tool_output else None
        sanitized_error = self.sanitize_secrets(error) if error else None

        if sanitized_error:
            self.errors.append(f"[{agent_name}] {sanitized_error}")

        step_entry = {
            "step_id": len(self.steps) + 1,
            "timestamp": time.strftime("%H:%M:%S"),
            "parent_agent": parent_agent,
            "agent": agent_name,
            "action": action,
            "tool": tool_name,
            "input": sanitized_input,
            "output": sanitized_output,
            "duration_sec": round(duration, 3) if duration else None,
            "retries": retries,
            "error": sanitized_error
        }
        self.steps.append(step_entry)

    def finish(self, status: str = "COMPLETED") -> Dict[str, Any]:
        """Finalize run and return summary metrics."""
        self.status = status
        total_duration = round(time.time() - self.start_time, 2)
        return {
            "run_id": self.run_id,
            "user_request": self.user_request,
            "status": self.status,
            "metrics": {
                "total_duration_sec": total_duration,
                "agent_calls": self.agent_calls_count,
                "mcp_tool_calls": self.tool_calls_count,
                "files_read": self.files_read_count,
                "retrieved_chunks": self.retrieved_chunks_count,
                "revision_cycles": self.revision_cycles_count,
                "test_execution_sec": round(self.test_execution_time, 2)
            },
            "errors": self.errors,
            "steps": self.steps
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get summary snapshot for UI visualization."""
        elapsed = round(time.time() - self.start_time, 1)
        return {
            "run_id": self.run_id,
            "status": self.status,
            "elapsed_sec": elapsed,
            "agent_calls": self.agent_calls_count,
            "tool_calls": self.tool_calls_count,
            "files_read": self.files_read_count,
            "retrieved_chunks": self.retrieved_chunks_count,
            "revision_cycles": self.revision_cycles_count,
            "latest_agent": self.steps[-1]["agent"] if self.steps else "Manager Agent",
            "latest_action": self.steps[-1]["action"] if self.steps else "Initializing..."
        }
