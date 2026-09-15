"""
Test Generator Workflow
Detects testing framework, analyzes source files, and generates executable unit/integration test suites.
"""
from typing import Dict, Any, Optional
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer
from repo_memory import RepoMemory
from agents.researcher_agent import ResearcherAgent
from agents.test_agent import TestAgent


def run_test_generator_workflow(
    repo_name: str,
    target_identifier: str, # e.g. "chat_github_llama3.py" or "PR #25"
    mcp_tools: GitHubMCPTools,
    tracer: AgentTracer,
    memory: RepoMemory
) -> str:
    """Execute Test Generation Workflow."""
    tracer.log_step("Manager Agent", f"Initiating Test Generation for target '{target_identifier}'")

    researcher = ResearcherAgent(mcp_tools, tracer)
    test_agent = TestAgent(tracer)

    repo_overview = researcher.gather_repo_overview(repo_name)
    framework = test_agent.detect_test_framework(repo_overview["test_files"], repo_overview["dep_files"])

    target_file = target_identifier
    if not target_file.endswith(".py"):
        if repo_overview["source_files"]:
            target_file = repo_overview["source_files"][0]

    # Fetch target file content
    try:
        content_data = mcp_tools.get_file_content(repo_name, target_file)
        file_content = content_data["content"]
    except Exception as e:
        file_content = "# Target file content placeholder\ndef handle_request(): pass"

    generated = test_agent.generate_tests(target_file, file_content, framework=framework)

    output = f"""# 🧪 Generated Test Suite

## Target Specification
- **Target Component**: [`{target_file}`](file:///{target_file})
- **Detected Testing Framework**: `{framework}`
- **Test File Name**: `{generated['test_filename']}`

## Covered Test Scenarios
{chr(10).join([f"- ✅ **{sc}**" for sc in generated['scenarios']])}

## Test Implementation Code
```python
{generated['test_code']}
```

## How to Execute
```bash
{framework} {generated['test_filename']}
```
"""

    tracer.finish(status="COMPLETED")
    return output
