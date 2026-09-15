"""
Pull Request Reviewer Workflow
Retrieves PR metadata, diffs, changed files, and generates a multi-dimensional code review.
"""
from typing import Dict, Any, Optional
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer
from repo_memory import RepoMemory
from agents.reviewer_agent import ReviewerAgent


def run_pr_reviewer_workflow(
    repo_name: str,
    pr_number: int,
    mcp_tools: GitHubMCPTools,
    tracer: AgentTracer,
    memory: RepoMemory
) -> str:
    """Execute AI Pull Request Review Workflow."""
    tracer.log_step("Manager Agent", f"Initiating PR Review for #{pr_number}")

    try:
        pr_data = mcp_tools.get_pull_request(repo_name, pr_number)
    except Exception as e:
        tracer.finish(status="FAILED")
        return f"❌ Failed to retrieve PR #{pr_number}: {str(e)}"

    reviewer = ReviewerAgent(tracer)
    review = reviewer.review_pr(pr_data)

    # Memory persistence
    memory.record_analyzed_pr(
        pr_number=pr_number,
        summary=pr_data['title'],
        recommendation=review['overall_assessment']
    )

    def format_finding(item):
        return f"- **[{item['severity']}]** `{item['file']}` ({item['location']}): {item['explanation']}\n  - *Fix*: {item['recommended_fix']}"

    crit = "\n".join([format_finding(i) for i in review["critical_issues"]]) if review["critical_issues"] else "None detected."
    warn = "\n".join([format_finding(i) for i in review["warnings"]]) if review["warnings"] else "None detected."
    sugg = "\n".join([format_finding(i) for i in review["suggestions"]]) if review["suggestions"] else "None."
    pos = "\n".join([f"- {p}" for p in review["positive_observations"]]) if review["positive_observations"] else "PR changes are clean and concise."
    miss = "\n".join([format_finding(i) for i in review["missing_tests"]]) if review["missing_tests"] else "All modified files have test coverage."

    output = f"""# 🔍 AI Pull Request Review: PR #{pr_number}

## PR Summary
**Title**: {pr_data['title']}  
**Author**: `{pr_data['user']}` | **Branches**: `{pr_data['head']}` ➔ `{pr_data['base']}`  
**Files Changed**: {len(pr_data.get('changed_files', []))}

## Overall Assessment
`{review['overall_assessment']}`

## Critical Issues
{crit}

## Warnings
{warn}

## Suggestions
{sugg}

## Positive Observations
{pos}

## Missing Tests
{miss}

## Final Recommendation
{review['final_recommendation']}
"""

    tracer.finish(status="COMPLETED")
    return output
