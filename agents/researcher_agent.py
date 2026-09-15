"""
Researcher Agent
Discovers repository structure, identifies key configuration/test/dependency files, and retrieves focused code context.
"""
import os
from typing import Dict, Any, List, Optional
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer
from repo_memory import RepoMemory


class ResearcherAgent:
    """
    Search-first context gathering agent for repository intelligence.
    """

    def __init__(self, mcp_tools: GitHubMCPTools, tracer: Optional[AgentTracer] = None):
        self.name = "Researcher Agent"
        self.mcp = mcp_tools
        self.tracer = tracer

    def gather_repo_overview(self, repo_name: str, branch: Optional[str] = None) -> Dict[str, Any]:
        """Inspect repository tree, categorize key files, and detect framework."""
        t0 = self.tracer.start_time if self.tracer else 0
        tree = self.mcp.get_repo_tree(repo_name, branch=branch, recursive=True)
        repo_info = self.mcp.get_repo_info(repo_name)

        config_files = []
        dep_files = []
        test_files = []
        source_files = []
        doc_files = []

        for item in tree:
            path = item["path"]
            path_lower = path.lower()
            if item["type"] != "blob":
                continue

            if path_lower.endswith((".md", ".rst", ".txt")) and ("readme" in path_lower or "doc" in path_lower):
                doc_files.append(path)
            elif path_lower in ["requirements.txt", "package.json", "pyproject.toml", "setup.py", "go.mod", "pom.xml", "cargo.toml"]:
                dep_files.append(path)
            elif any(k in path_lower for k in [".env.example", "dockerfile", "docker-compose", "config", "settings", "tsconfig.json"]):
                config_files.append(path)
            elif "test" in path_lower or path_lower.startswith("tests/"):
                test_files.append(path)
            elif any(path_lower.endswith(ext) for ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".c", ".cpp", ".rs"]):
                source_files.append(path)

        # Calculate language extension distribution dynamically
        ext_counts = {}
        for f in source_files:
            ext = os.path.splitext(f)[1].lower()
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

        ext_to_lang = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "React/JavaScript",
            ".tsx": "React/TypeScript",
            ".go": "Go",
            ".rs": "Rust",
            ".java": "Java",
            ".kt": "Kotlin",
            ".c": "C",
            ".cpp": "C++",
            ".h": "C/C++ Header",
            ".php": "PHP",
            ".rb": "Ruby",
            ".html": "HTML",
            ".css": "CSS"
        }

        detected_lang = repo_info.get("language")
        if not detected_lang and ext_counts:
            top_ext = max(ext_counts, key=ext_counts.get)
            detected_lang = ext_to_lang.get(top_ext, "Python")
        if not detected_lang:
            detected_lang = "Python"

        # Detect primary framework dynamically
        detected_framework = "Generic Application"
        all_file_names = " ".join([f.lower() for f in source_files + dep_files + config_files])
        if "streamlit" in all_file_names:
            detected_framework = "Streamlit"
        elif "fastapi" in all_file_names:
            detected_framework = "FastAPI"
        elif "flask" in all_file_names:
            detected_framework = "Flask"
        elif "django" in all_file_names:
            detected_framework = "Django"
        elif "next" in all_file_names or "react" in all_file_names:
            detected_framework = "React / Next.js"
        elif "express" in all_file_names:
            detected_framework = "Express / Node.js"
        elif any("package.json" in f for f in dep_files):
            detected_framework = "Node.js"
        elif any("go.mod" in f for f in dep_files):
            detected_framework = "Go Module"
        elif any("cargo.toml" in f for f in dep_files):
            detected_framework = "Cargo / Rust"

        overview = {
            "repo_name": repo_name,
            "primary_language": detected_lang,
            "detected_framework": detected_framework,
            "total_files": len(tree),
            "doc_files": doc_files[:5],
            "dep_files": dep_files[:5],
            "config_files": config_files[:5],
            "test_files": test_files[:15],
            "source_files": source_files[:30]
        }

        if self.tracer:
            self.tracer.log_step(
                agent_name=self.name,
                action=f"Scanned repo tree: {len(tree)} items found",
                tool_name="get_repo_tree",
                tool_output=overview
            )

        return overview

    def search_relevant_context(self, repo_name: str, query: str, max_files: int = 5) -> List[Dict[str, Any]]:
        """Search code for keywords and retrieve contents of matching files."""
        search_results = self.mcp.search_code(repo_name, query, max_results=max_files)
        fetched_files = []

        for item in search_results:
            path = item["path"]
            try:
                content_data = self.mcp.get_file_content(repo_name, path)
                fetched_files.append({
                    "path": path,
                    "content": content_data["content"]
                })
            except Exception as e:
                if self.tracer:
                    self.tracer.log_step(
                        agent_name=self.name,
                        action=f"Failed to read file {path}",
                        error=str(e)
                    )

        if self.tracer:
            self.tracer.log_step(
                agent_name=self.name,
                action=f"Found and retrieved {len(fetched_files)} relevant files for query '{query}'",
                tool_name="search_code",
                tool_output=[f["path"] for f in fetched_files]
            )

        return fetched_files
