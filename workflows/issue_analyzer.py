"""
Issue Analyzer Workflow
Investigates GitHub issues, extracts keywords/stacktraces, inspects repository code, and returns root-cause diagnosis.
"""
from typing import Dict, Any, Optional
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer
from repo_memory import RepoMemory
from agents.researcher_agent import ResearcherAgent
from agents.analyzer_agent import AnalyzerAgent


def run_issue_analyzer_workflow(
    repo_name: str,
    issue_number: int,
    mcp_tools: GitHubMCPTools,
    tracer: AgentTracer,
    memory: RepoMemory
) -> str:
    """Execute Issue Investigation Workflow."""
    tracer.log_step("Manager Agent", f"Initiating Issue Analysis for #{issue_number}")

    # Fetch Issue data via MCP
    try:
        issue_data = mcp_tools.get_issue(repo_name, issue_number)
    except Exception as e:
        tracer.finish(status="FAILED")
        return f"❌ Failed to retrieve Issue #{issue_number}: {str(e)}"

    researcher = ResearcherAgent(mcp_tools, tracer)
    analyzer = AnalyzerAgent(tracer)

    # Search for code relevant to issue title and body
    query = f"{issue_data['title']} {' '.join(issue_data.get('labels', []))}"
    relevant_files = researcher.search_relevant_context(repo_name, query, max_files=5)

    # If search turned up empty, fallback to main source files
    if not relevant_files:
        overview = researcher.gather_repo_overview(repo_name)
        if overview["source_files"]:
            main_file = overview["source_files"][0]
            content = mcp_tools.get_file_content(repo_name, main_file)
            relevant_files = [content]

    # Perform analysis
    diag = analyzer.analyze_issue(issue_data, relevant_files)

    # Persist into memory
    memory.record_analyzed_issue(
        issue_number=issue_number,
        summary=issue_data['title'],
        root_cause=diag['likely_root_cause']
    )

    # Format Exact Master Prompt Output Structure
    output = f"""# 🐛 Issue Analysis Report: Issue #{issue_number}

## Issue Summary
**Title**: {issue_data['title']}  
**Reporter**: `{issue_data['user']}` | **State**: `{issue_data['state']}`  
**Description**:  
> {issue_data['body'] or 'No description provided.'}

## Relevant Files
{chr(10).join([f"- [`{f['path']}`](file:///{f['path']})" for f in relevant_files])}

## Investigation
{diag['investigation']}

## Likely Root Cause
{diag['likely_root_cause']}

## Evidence
- **Confirmed Facts**:
{chr(10).join([f"  - {fact}" for fact in diag['confirmed_facts']])}
- **Hypotheses**:
{chr(10).join([f"  - {h}" for h in diag['hypotheses']])}

## Recommended Fix
{diag['recommended_fix_strategy']}

## Potential Risks
{chr(10).join([f"- {r}" for r in diag['potential_risks']])}

## Suggested Tests
- Add unit tests validating parameter input ranges.
- Add regression test case verifying Issue #{issue_number} behavior.
"""

    tracer.finish(status="COMPLETED")
    return output
