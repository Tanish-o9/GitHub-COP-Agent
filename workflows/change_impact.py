"""
Change Impact Analysis Workflow
Calculates direct dependencies, caller files, related tests, and regression risks for proposed code changes.
"""
from typing import Dict, Any, Optional
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer
from repo_memory import RepoMemory
from agents.researcher_agent import ResearcherAgent
from dependency_analyzer import DependencyAnalyzer


def run_change_impact_workflow(
    repo_name: str,
    target_file: str,
    mcp_tools: GitHubMCPTools,
    tracer: AgentTracer,
    memory: RepoMemory
) -> str:
    """Execute Change Impact Analysis Workflow."""
    tracer.log_step("Manager Agent", f"Starting Change Impact Analysis for target '{target_file}'")

    researcher = ResearcherAgent(mcp_tools, tracer)
    overview = researcher.gather_repo_overview(repo_name)

    # Clean target file path
    clean_target = target_file
    for word in target_file.split():
        if word.endswith(".py"):
            clean_target = word
            break

    # Fetch repo source files context
    repo_files = []
    for path in overview["source_files"][:10] + overview["test_files"][:10]:
        try:
            fc = mcp_tools.get_file_content(repo_name, path)
            repo_files.append(fc)
        except Exception:
            pass

    # Run Dependency & Impact Analysis
    report = DependencyAnalyzer.analyze_change_impact(clean_target, repo_files)
    markdown_output = DependencyAnalyzer.format_impact_markdown(report)

    tracer.finish(status="COMPLETED")
    return markdown_output
