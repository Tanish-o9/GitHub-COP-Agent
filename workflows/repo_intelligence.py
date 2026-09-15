"""
Repository Intelligence Workflow
Executes repo structure discovery, search-first file inspection, architecture analysis, and memory persistence.
"""
from typing import Dict, Any, Optional
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer
from repo_memory import RepoMemory
from agents.researcher_agent import ResearcherAgent
from agents.analyzer_agent import AnalyzerAgent


def run_repo_intelligence_workflow(
    repo_name: str,
    query: str,
    mcp_tools: GitHubMCPTools,
    tracer: AgentTracer,
    memory: RepoMemory,
    branch: Optional[str] = None
) -> str:
    """Execute search-first repository intelligence workflow."""
    tracer.log_step("Manager Agent", f"Starting Repository Intelligence for '{repo_name}'")

    researcher = ResearcherAgent(mcp_tools, tracer)
    analyzer = AnalyzerAgent(tracer)

    # Step 1: Repo Tree & Framework Scan
    repo_overview = researcher.gather_repo_overview(repo_name, branch=branch)
    
    # Step 2: Search relevant files based on user query
    relevant_files = researcher.search_relevant_context(repo_name, query, max_files=4)

    # Step 3: Architectural Analysis & Targeted Answer Synthesis
    arch_analysis = analyzer.analyze_architecture(repo_overview, relevant_files)
    query_answer = analyzer.answer_user_query(query, repo_overview, relevant_files)

    # Step 4: Persist insights to Durable Memory
    memory.update_architecture_insights(
        architecture=arch_analysis["architecture_overview"],
        language=arch_analysis["primary_language"],
        framework=arch_analysis["framework"],
        auth_flow=arch_analysis["auth_flow"]
    )

    # Format Markdown Output
    output_lines = [
        f"# 🏛️ Repository Intelligence: `{repo_name}`",
        "",
        query_answer,
        "",
        "---",
        "## 🏗️ Repository Architecture & Overview",
        f"- **Primary Language**: `{arch_analysis['primary_language']}`",
        f"- **Detected Framework**: `{arch_analysis['framework']}`",
        f"- **Default Branch**: `{branch or 'main'}`",
        "",
        "### Overview Details",
        arch_analysis["architecture_overview"],
        "",
        "## 📂 Discovered Relevant Source Components",
    ]

    for f in relevant_files:
        output_lines.append(f"- **[`{f['path']}`](file:///{f['path']})**")
        snippet_lines = f.get("content", "").splitlines()[:15]
        if snippet_lines:
            snippet = "\n".join(snippet_lines)
            output_lines.append(f"```python\n{snippet}\n```\n")

    output_lines.extend([
        "## 🔒 Persistent Memory Updated",
        f"Saved repository architecture and `{arch_analysis['primary_language']}` context into durable memory `.repo_memory/`."
    ])

    tracer.finish(status="COMPLETED")
    return "\n".join(output_lines)
