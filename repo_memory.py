"""
Advanced Repository Memory Module — Phase 3
Categorized, version-aware, secret-free memory module enforcing Current Code > Old Memory conflict resolution.
"""
import os
import json
import time
from typing import Dict, Any, List, Optional
from agent_tracer import AgentTracer


class RepoMemory:
    """
    Manages categorized, version-aware durable memory per repository.
    """

    def __init__(self, repo_name: str, branch: str = "main", memory_dir: str = ".repo_memory"):
        self.repo_name = repo_name.strip().strip("/")
        self.branch = branch
        self.clean_id = self.repo_name.replace("/", "_").replace("\\", "_")
        self.memory_dir = memory_dir
        os.makedirs(self.memory_dir, exist_ok=True)
        self.filepath = os.path.join(self.memory_dir, f"{self.clean_id}.json")
        self.memory_data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load durable categorized repository memory from disk."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data
            except Exception:
                pass
        return {
            "repo_name": self.repo_name,
            "branch": self.branch,
            "commit_sha": "latest",
            "indexing_timestamp": time.time(),
            "repository_facts": {
                "primary_language": "",
                "framework": "",
                "database": ""
            },
            "architecture_knowledge": {
                "overview": "",
                "auth_flow": "",
                "data_flow": ""
            },
            "project_conventions": {
                "testing_framework": "pytest",
                "code_style": "PEP8"
            },
            "historical_knowledge": {
                "analyzed_issues": [],
                "analyzed_prs": []
            },
            "user_preferences": {}
        }

    def save(self) -> None:
        """Persist sanitized memory data to disk."""
        self.memory_data["indexing_timestamp"] = time.time()
        sanitized_json_str = AgentTracer.sanitize_secrets(json.dumps(self.memory_data, indent=2))
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.write(sanitized_json_str)
        except Exception:
            pass

    def update_facts(self, language: Optional[str] = None, framework: Optional[str] = None, database: Optional[str] = None) -> None:
        """Update Repository Facts (enforces Live Code > Old Memory)."""
        facts = self.memory_data["repository_facts"]
        if language:
            facts["primary_language"] = language
        if framework:
            facts["framework"] = framework
        if database:
            facts["database"] = database
        self.save()

    def update_architecture(self, overview: Optional[str] = None, auth_flow: Optional[str] = None, data_flow: Optional[str] = None) -> None:
        """Update Architecture Knowledge."""
        arch = self.memory_data["architecture_knowledge"]
        if overview:
            arch["overview"] = AgentTracer.sanitize_secrets(overview)
        if auth_flow:
            arch["auth_flow"] = AgentTracer.sanitize_secrets(auth_flow)
        if data_flow:
            arch["data_flow"] = AgentTracer.sanitize_secrets(data_flow)
        self.save()

    def update_architecture_insights(self, architecture: Optional[str] = None, language: Optional[str] = None, framework: Optional[str] = None, auth_flow: Optional[str] = None) -> None:
        """Update facts and architecture insights simultaneously."""
        self.update_facts(language=language, framework=framework)
        self.update_architecture(overview=architecture, auth_flow=auth_flow)

    def record_analyzed_issue(self, issue_number: int, summary: str, root_cause: str) -> None:
        """Save historical issue resolution context."""
        entry = {
            "issue_number": issue_number,
            "summary": AgentTracer.sanitize_secrets(summary),
            "root_cause": AgentTracer.sanitize_secrets(root_cause),
            "timestamp": time.time()
        }
        hist = self.memory_data["historical_knowledge"]["analyzed_issues"]
        self.memory_data["historical_knowledge"]["analyzed_issues"] = [
            i for i in hist if i.get("issue_number") != issue_number
        ]
        self.memory_data["historical_knowledge"]["analyzed_issues"].append(entry)
        self.save()

    def record_analyzed_pr(self, pr_number: int, summary: str, recommendation: str) -> None:
        """Save historical PR review context."""
        entry = {
            "pr_number": pr_number,
            "summary": AgentTracer.sanitize_secrets(summary),
            "recommendation": AgentTracer.sanitize_secrets(recommendation),
            "timestamp": time.time()
        }
        prs = self.memory_data["historical_knowledge"]["analyzed_prs"]
        self.memory_data["historical_knowledge"]["analyzed_prs"] = [
            p for p in prs if p.get("pr_number") != pr_number
        ]
        self.memory_data["historical_knowledge"]["analyzed_prs"].append(entry)
        self.save()

    def get_context_summary(self) -> str:
        """Format categorized memory into readable prompt context."""
        facts = self.memory_data.get("repository_facts", {})
        arch = self.memory_data.get("architecture_knowledge", {})
        conv = self.memory_data.get("project_conventions", {})
        
        parts = []
        if facts.get("primary_language"):
            parts.append(f"- **Facts**: Language: `{facts['primary_language']}` | Framework: `{facts['framework']}` | DB: `{facts['database'] or 'None'}`")
        if arch.get("overview"):
            parts.append(f"- **Architecture**: {arch['overview']}")
        if conv.get("testing_framework"):
            parts.append(f"- **Conventions**: Testing: `{conv['testing_framework']}` | Style: `{conv['code_style']}`")

        return "\n".join(parts) if parts else "No prior repository memory saved."
