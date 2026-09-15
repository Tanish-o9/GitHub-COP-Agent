"""
End-to-End Software Engineering Workflow — Phase 3
Integrates Codebase RAG, Smart Context Builder, Dependency Analyzer, Security Gate, and Human Approval.
"""
from typing import Dict, Any, Optional
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer
from repo_memory import RepoMemory
from repo_cache import RepoCache
from agent_state import AgentState, WorkflowState
from human_approval import HumanApprovalRequest, ApprovalStatus
from security_gate import SecurityGate
from rag_engine import CodebaseRAGEngine
from dependency_analyzer import DependencyAnalyzer
from context_builder import SmartContextBuilder
from agents.researcher_agent import ResearcherAgent
from agents.analyzer_agent import AnalyzerAgent
from agents.coder_agent import CoderAgent
from agents.test_agent import TestAgent
from agents.reviewer_agent import ReviewerAgent


def prepare_engineering_fix_stateful(
    state: AgentState,
    mcp_tools: GitHubMCPTools,
    tracer: AgentTracer,
    memory: RepoMemory,
    max_revisions: int = 3
) -> AgentState:
    """
    Phase 3 Stateful Pipeline: RAG Indexing -> Smart Context -> Plan -> Code -> Test -> Review -> Impact -> Security -> Approval.
    """
    state.max_revisions = max_revisions
    tracer.log_step("Manager Agent", f"Initiating Stateful Engineering Workflow for '{state.repo_name}'")

    researcher = ResearcherAgent(mcp_tools, tracer)
    analyzer = AnalyzerAgent(tracer)
    coder = CoderAgent(tracer)
    test_agent = TestAgent(tracer)
    reviewer = ReviewerAgent(tracer)

    # 1. RAG Indexing & Hybrid Retrieval
    rag = CodebaseRAGEngine(state.repo_name, branch=state.branch)
    try:
        rag.index_repository(mcp_tools, max_files=15)
        rag_chunks = rag.hybrid_search(state.user_request, top_k=3)
        tracer.retrieved_chunks_count = len(rag_chunks)
    except Exception:
        rag_chunks = []

    # 2. Fetch Target Issue or Context
    state.transition_to(WorkflowState.ANALYZING)
    if state.issue_number:
        try:
            issue_data = mcp_tools.get_issue(state.repo_name, state.issue_number)
            query = issue_data["title"]
        except Exception:
            issue_data = {"number": state.issue_number, "title": state.user_request, "body": state.user_request}
            query = state.user_request
    else:
        issue_data = {"number": 0, "title": state.user_request, "body": state.user_request}
        query = state.user_request

    # Retrieve context
    cached_tree = RepoCache.get(state.repo_name, "tree")
    if not cached_tree:
        relevant = researcher.search_relevant_context(state.repo_name, query, max_files=3)
        RepoCache.set(state.repo_name, "tree", relevant)
    else:
        relevant = cached_tree

    if not relevant:
        overview = researcher.gather_repo_overview(state.repo_name)
        target_path = overview["source_files"][0] if overview["source_files"] else "chat_github_llama3.py"
        try:
            content_data = mcp_tools.get_file_content(state.repo_name, target_path)
            relevant = [content_data]
        except Exception:
            relevant = [{"path": target_path, "content": "# Core application logic"}]

    target_file_data = relevant[0]
    target_path = target_file_data["path"]
    original_content = target_file_data.get("content")
    if original_content is None:
        try:
            fc = mcp_tools.get_file_content(state.repo_name, target_path)
            original_content = fc.get("content", "# Core application logic")
        except Exception:
            original_content = "# Core application logic"

    state.relevant_files = [target_file_data]

    # Dependency Change Impact Analysis
    impact_report = DependencyAnalyzer.analyze_change_impact(target_path, relevant)

    # Smart Context Synthesis
    smart_context = SmartContextBuilder.build_focused_context(
        user_request=state.user_request,
        repo_name=state.repo_name,
        memory=memory,
        rag_chunks=rag_chunks,
        relevant_files=relevant,
        dependency_info=impact_report,
        issue_data=issue_data
    )
    state.code_context = {"smart_context": smart_context["raw_text"]}

    # Analysis
    diag = analyzer.analyze_issue(issue_data, relevant)
    state.issue_analysis = diag
    state.root_cause = diag["likely_root_cause"]

    # 3. Formulate Implementation Plan
    state.transition_to(WorkflowState.PLANNING)
    plan_steps = coder.generate_implementation_plan(
        issue_title=issue_data["title"],
        target_path=target_path,
        root_cause=state.root_cause
    )
    state.implementation_plan = plan_steps

    # 4. Code Generation & Revision Loop
    revision_feedback = None
    state.revision_count = 0

    while state.revision_count <= state.max_revisions:
        state.transition_to(WorkflowState.IMPLEMENTING if state.revision_count == 0 else WorkflowState.REVISION_REQUIRED)
        
        fix_plan = coder.propose_fix(
            target_file=target_path,
            original_content=original_content,
            fix_description=f"Fix for Issue #{issue_data['number']}: {issue_data['title']}",
            revision_feedback=revision_feedback
        )
        state.proposed_changes = {target_path: fix_plan["modified_content"]}

        # Test Generation & Execution
        state.transition_to(WorkflowState.TESTING)
        test_plan = test_agent.generate_tests(target_path, fix_plan["modified_content"])
        state.generated_tests = {test_plan["test_filename"]: test_plan["test_code"]}

        test_results = test_agent.run_tests(
            test_filename=test_plan["test_filename"],
            test_code=test_plan["test_code"],
            target_filename=target_path,
            target_code=fix_plan["modified_content"]
        )
        state.test_results = test_results

        # Review Evaluation
        state.transition_to(WorkflowState.REVIEWING)
        patch_review = reviewer.review_proposed_patch(fix_plan)
        state.review_findings = patch_review

        if patch_review["is_approved"] and test_results.get("passed", True):
            break
        else:
            state.revision_count += 1
            tracer.revision_cycles_count += 1
            if state.revision_count > state.max_revisions:
                break
            revision_feedback = f"Reviewer findings: {', '.join(patch_review.get('findings', ['Needs refinement']))}"

    # 5. Security Gate Check
    state.transition_to(WorkflowState.SECURITY_CHECK)
    sec_audit = SecurityGate.audit_patch(target_path, fix_plan["modified_content"])
    state.security_findings = sec_audit

    if not sec_audit["passed"]:
        state.add_error("SECURITY REVIEW FAILED: Critical vulnerability detected in proposed patch.")
        tracer.finish(status="FAILED")
        return state

    # 6. Human Approval Checkpoint
    state.transition_to(WorkflowState.WAITING_FOR_APPROVAL)
    clean_slug = "".join(c if c.isalnum() else "-" for c in issue_data["title"].lower())[:25].strip("-")
    safe_branch_name = f"ai-fix/issue-{issue_data['number'] or 'patch'}-{clean_slug}"
    state.branch_name = safe_branch_name

    approval_req = HumanApprovalRequest(
        action_type="CREATE_SAFE_BRANCH_AND_PR",
        repo_name=state.repo_name,
        target_branch=safe_branch_name,
        files_to_change=[target_path, test_plan["test_filename"]],
        change_summary=f"Resolved issue '{issue_data['title']}' via RAG-enhanced multi-agent workflow.",
        generated_tests=test_plan["scenarios"],
        potential_risks=impact_report["regression_risks"],
        patch_payload={
            "target_path": target_path,
            "modified_content": fix_plan["modified_content"],
            "test_filename": test_plan["test_filename"],
            "test_code": test_plan["test_code"],
            "branch_name": safe_branch_name,
            "base_branch": state.branch,
            "issue_title": issue_data["title"]
        }
    )

    tracer.log_step("Manager Agent", "Prepared Engineering Fix and created Human Approval Checkpoint", tool_output=approval_req.to_dict())
    return state


def execute_approved_engineering_fix_stateful(
    approval_req: Any,
    mcp_tools: GitHubMCPTools,
    tracer: AgentTracer
) -> str:
    """
    Executes an approved engineering fix:
    1. Creates safe feature branch (e.g. ai-fix/issue-X-slug)
    2. Commits modified code and test files
    3. Opens Pull Request
    """
    if isinstance(approval_req, dict):
        payload = approval_req.get("patch_payload", {})
        repo_name = approval_req.get("repo_name", "")
        summary = approval_req.get("change_summary", "Automated Engineering Fix")
    else:
        payload = getattr(approval_req, "patch_payload", {})
        repo_name = getattr(approval_req, "repo_name", "")
        summary = getattr(approval_req, "change_summary", "Automated Engineering Fix")

    target_path = payload.get("target_path")
    modified_content = payload.get("modified_content")
    test_filename = payload.get("test_filename")
    test_code = payload.get("test_code")
    branch_name = payload.get("branch_name", "ai-fix/patch")
    base_branch = payload.get("base_branch", "main")
    issue_title = payload.get("issue_title", "Automated Fix")

    tracer.log_step("Manager Agent", f"Executing approved mutation on branch '{branch_name}'")

    # 1. Create Branch
    try:
        mcp_tools.create_branch(repo_name, branch_name, base_branch=base_branch)
    except Exception as e:
        tracer.log_step("Manager Agent", f"Branch creation warning: {e}")

    # 2. Commit Files
    if target_path and modified_content:
        mcp_tools.commit_file_changes(
            repo_name=repo_name,
            file_path=target_path,
            content=modified_content,
            commit_message=f"fix: {issue_title}",
            branch=branch_name
        )

    if test_filename and test_code:
        mcp_tools.commit_file_changes(
            repo_name=repo_name,
            file_path=test_filename,
            content=test_code,
            commit_message=f"test: add verification tests for {issue_title}",
            branch=branch_name
        )

    # 3. Create PR
    pr_res = mcp_tools.create_pull_request(
        repo_name=repo_name,
        title=f"AI Fix: {issue_title}",
        body=f"## Summary\n{summary}\n\n*Generated by Autonomous AI Software Engineering Platform*",
        head_branch=branch_name,
        base_branch=base_branch
    )

    pr_url = pr_res.get("html_url") or pr_res.get("url") or f"PR on {branch_name}"
    tracer.log_step("Manager Agent", f"Successfully created PR: {pr_url}")
    tracer.finish(status="SUCCESS")
    return f"Successfully created branch '{branch_name}' and opened Pull Request: {pr_url}"

