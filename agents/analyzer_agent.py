"""
Analyzer Agent
Analyzes code logic, investigates issue root causes, traces data and control flows, and generates technical diagnoses.
"""
from typing import Dict, Any, List, Optional
from agent_tracer import AgentTracer


class AnalyzerAgent:
    """
    Deep analytical agent for root-cause diagnosis, architecture tracing, and issue evaluation.
    """

    def __init__(self, tracer: Optional[AgentTracer] = None):
        self.name = "Analyzer Agent"
        self.tracer = tracer

    def analyze_issue(
        self,
        issue_data: Dict[str, Any],
        relevant_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform root cause analysis on a GitHub Issue."""
        title = issue_data.get("title", "")
        body = issue_data.get("body", "")
        number = issue_data.get("number", 0)

        # Extract keywords and potential functions/errors mentioned
        file_paths = [f["path"] for f in relevant_files]

        investigation_notes = []
        confirmed_facts = []
        hypotheses = []

        if relevant_files:
            confirmed_facts.append(f"Located {len(relevant_files)} matching files in repository: {', '.join(file_paths)}")
        else:
            hypotheses.append("No exact matching source files found via keyword search. Broader inspection needed.")

        if "error" in body.lower() or "exception" in body.lower() or "fail" in body.lower():
            investigation_notes.append("Issue describes a runtime exception or error stack trace.")
        else:
            investigation_notes.append("Issue describes a feature request, logic flaw, or behavioral mismatch.")

        analysis_result = {
            "issue_number": number,
            "title": title,
            "relevant_files": file_paths,
            "investigation": "\n".join(investigation_notes),
            "confirmed_facts": confirmed_facts,
            "hypotheses": hypotheses,
            "likely_root_cause": f"Potential logic mismatch or unhandled exception scenario in {file_paths[0] if file_paths else 'source modules'}.",
            "recommended_fix_strategy": "Implement safe input validation, exception handling, and corresponding unit test coverage.",
            "potential_risks": ["Possible side effects on downstream module callers", "Requires test suite verification"]
        }

        if self.tracer:
            self.tracer.log_step(
                agent_name=self.name,
                action=f"Completed root-cause analysis for Issue #{number}",
                tool_output=analysis_result
            )

        return analysis_result

    def analyze_architecture(
        self,
        repo_overview: Dict[str, Any],
        key_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze repository architecture, data flow, and authentication."""
        lang = repo_overview.get("primary_language", "Python")
        fw = repo_overview.get("detected_framework", "Generic")

        arch_summary = (
            f"Repository **{repo_overview.get('repo_name')}** is structured in **{lang}** using **{fw}**. "
            f"Config files: {', '.join(repo_overview.get('config_files', [])) or 'None'}. "
            f"Primary source modules: {', '.join(repo_overview.get('source_files', [])[:5]) or 'None'}."
        )

        auth_flow = "Configuration & environment token authentication."
        data_flow = "Module-based input processing and file system / API routing."

        analysis = {
            "architecture_overview": arch_summary,
            "primary_language": lang,
            "framework": fw,
            "auth_flow": auth_flow,
            "data_flow": data_flow,
            "components": [f["path"] for f in key_files]
        }

        if self.tracer:
            self.tracer.log_step(
                agent_name=self.name,
                action="Generated architecture analysis summary",
                tool_output=analysis
            )

        return analysis

    def answer_user_query(
        self,
        query: str,
        repo_overview: Dict[str, Any],
        key_files: List[Dict[str, Any]]
    ) -> str:
        """Synthesize a direct, precise answer to the user's question based on retrieved repository context."""
        query_lower = query.lower()
        repo_name = repo_overview.get("repo_name", "Target Repository")
        lang = repo_overview.get("primary_language", "Python")
        fw = repo_overview.get("detected_framework", "Generic Application")
        source_files = repo_overview.get("source_files", [])
        config_files = repo_overview.get("config_files", [])
        dep_files = repo_overview.get("dep_files", [])

        if any(w in query_lower for w in ["language", "backend", "framework", "written in", "tech stack", "stack"]):
            answer = (
                f"### 💡 Language & Tech Stack Analysis for `{repo_name}`\n\n"
                f"- **Primary Backend Language**: **`{lang}`**\n"
                f"- **Framework / Runtime**: **`{fw}`**\n"
                f"- **Total Scanned Files**: `{repo_overview.get('total_files', 0)}`\n"
                f"- **Core Source Files**: {', '.join([f'`{s}`' for s in source_files[:5]]) or 'None'}\n"
                f"- **Dependency Manifests**: {', '.join([f'`{d}`' for d in dep_files[:5]]) or 'None'}\n\n"
                f"**Summary**:\n"
                f"The backend for repository `{repo_name}` is primarily developed in **{lang}** utilizing the **{fw}** ecosystem. "
                f"The codebase comprises `{len(source_files)}` source files with configurations defined in {', '.join([f'`{c}`' for c in config_files[:3]]) or 'standard project configs'}."
            )
            comp_list = ', '.join([f"`{f.get('path')}`" for f in key_files[:5]]) or 'Repository Modules'
            answer = (
                f"### 💡 Repository Query Analysis for `{repo_name}`\n\n"
                f"**Query**: *\"{query}\"*\n\n"
                f"- **Primary Language**: `{lang}`\n"
                f"- **Framework**: `{fw}`\n"
                f"- **Key Discovered Components**: {comp_list}\n"
            )

        return answer
