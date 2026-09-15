"""
Specialist Agent Registry
Manages registration and dynamic selection of specialized agent roles (Repository Analyst, Bug Investigator, Coder, Reviewer, Security, Test Impact).
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SpecialistAgentSpec:
    """Specifies capabilities and constraints for a specialist agent."""
    name: str
    role_type: str
    description: str
    allowed_tools: List[str] = field(default_factory=list)
    risk_level: str = "LOW"
    output_schema: str = "JSON/Markdown"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SpecialistAgentRegistry:
    """Dynamic registry for selecting minimal capable agent sets."""

    _registry: Dict[str, SpecialistAgentSpec] = {}

    @classmethod
    def register(cls, spec: SpecialistAgentSpec):
        cls._registry[spec.role_type] = spec

    @classmethod
    def get(cls, role_type: str) -> Optional[SpecialistAgentSpec]:
        return cls._registry.get(role_type)

    @classmethod
    def select_specialists(cls, task_type: str) -> List[SpecialistAgentSpec]:
        """Dynamically select minimal capable set of specialist agents for a task."""
        selected = []
        if task_type in ["FULL_ENGINEERING_WORKFLOW", "CODE_IMPLEMENTATION"]:
            selected = [
                cls._registry.get("FEATURE_PLANNER"),
                cls._registry.get("CODING_AGENT"),
                cls._registry.get("TEST_AGENT"),
                cls._registry.get("CODE_REVIEWER"),
                cls._registry.get("SECURITY_AGENT")
            ]
        elif task_type in ["ISSUE_ANALYSIS", "BUG_INVESTIGATION"]:
            selected = [
                cls._registry.get("BUG_INVESTIGATOR"),
                cls._registry.get("REPOSITORY_ANALYST")
            ]
        elif task_type in ["PR_REVIEW"]:
            selected = [
                cls._registry.get("CODE_REVIEWER"),
                cls._registry.get("SECURITY_AGENT")
            ]
        elif task_type in ["SECURITY_AUDIT"]:
            selected = [cls._registry.get("SECURITY_AGENT")]
        else:
            selected = [cls._registry.get("REPOSITORY_ANALYST")]

        return [s for s in selected if s is not None]


# Default Registration
SpecialistAgentRegistry.register(SpecialistAgentSpec(
    name="Repository Analyst",
    role_type="REPOSITORY_ANALYST",
    description="Analyzes codebase structure, modules, imports, and symbol dependencies.",
    allowed_tools=["get_repo_info", "get_repo_tree", "search_code", "get_file_content"]
))

SpecialistAgentRegistry.register(SpecialistAgentSpec(
    name="Bug Investigator",
    role_type="BUG_INVESTIGATOR",
    description="Investigates issue reports, stack traces, and pinpoints root causes.",
    allowed_tools=["get_issue", "get_file_content", "search_code"]
))

SpecialistAgentRegistry.register(SpecialistAgentSpec(
    name="Feature Planner",
    role_type="FEATURE_PLANNER",
    description="Formulates step-by-step engineering implementation plans.",
    allowed_tools=["search_code", "get_file_content"]
))

SpecialistAgentRegistry.register(SpecialistAgentSpec(
    name="Coding Agent",
    role_type="CODING_AGENT",
    description="Generates precise Python code patches.",
    allowed_tools=["commit_file_changes"]
))

SpecialistAgentRegistry.register(SpecialistAgentSpec(
    name="Test Agent",
    role_type="TEST_AGENT",
    description="Discovers and executes unit/integration tests.",
    allowed_tools=["run_command", "commit_file_changes"]
))

SpecialistAgentRegistry.register(SpecialistAgentSpec(
    name="Code Reviewer",
    role_type="CODE_REVIEWER",
    description="Reviews proposed patches for bugs, style, and correctness.",
    allowed_tools=["get_pull_request", "get_file_content"]
))

SpecialistAgentRegistry.register(SpecialistAgentSpec(
    name="Security Agent",
    role_type="SECURITY_AGENT",
    description="Audits patches for OWASP vulnerabilities and secret leaks.",
    allowed_tools=["get_file_content"]
))
