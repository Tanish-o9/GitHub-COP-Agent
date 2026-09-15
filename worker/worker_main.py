"""
Async Background Worker Engine
Executes multi-agent workflows in background tasks, updating database states and broadcasting real-time progress events.
"""
import os
import sys
import time
import asyncio
from typing import Dict, Any, Optional

# Insert parent dir to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import SessionLocal
from database.models import AgentRun, AgentStep, Approval, AuditLog
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer
from repo_memory import RepoMemory
from agent_state import AgentState, WorkflowState
from agents.manager_agent import ManagerAgent
from workflows.repo_intelligence import run_repo_intelligence_workflow
from workflows.issue_analyzer import run_issue_analyzer_workflow
from workflows.pr_reviewer import run_pr_reviewer_workflow
from workflows.test_generator import run_test_generator_workflow
from workflows.security_auditor import run_security_auditor_workflow
from workflows.change_impact import run_change_impact_workflow
from workflows.engineering_workflow import prepare_engineering_fix_stateful
from api.websocket import ws_manager


def execute_agent_run_task(run_id: str, repo_name: str, user_prompt: str, branch: str = "main", github_token: Optional[str] = None):
    """
    Background worker entry point for executing an AgentRun.
    """
    db = SessionLocal()
    run_record = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run_record:
        db.close()
        return

    run_record.status = "RUNNING"
    run_record.updated_at = time.time()
    db.commit()

    # Broadcast WebSocket run.started
    asyncio.run(ws_manager.broadcast_run_event(run_id, "run.started", {"prompt": user_prompt, "repo": repo_name}))

    tracer = AgentTracer(user_prompt)
    mcp_tools = GitHubMCPTools(token=github_token)
    memory = RepoMemory(repo_name, branch=branch)
    manager = ManagerAgent(tracer)

    classification = manager.classify_request(user_prompt)
    workflow_type = classification["workflow"]
    run_record.workflow_type = workflow_type
    db.commit()

    try:
        if workflow_type == "CHANGE_IMPACT":
            output_md = run_change_impact_workflow(repo_name, "chat_github_llama3.py", mcp_tools, tracer, memory)
            run_record.status = "COMPLETED"
        elif workflow_type == "REPO_INTELLIGENCE":
            output_md = run_repo_intelligence_workflow(repo_name, user_prompt, mcp_tools, tracer, memory, branch=branch)
            run_record.status = "COMPLETED"
        elif workflow_type == "ISSUE_ANALYSIS":
            output_md = run_issue_analyzer_workflow(repo_name, 1, mcp_tools, tracer, memory)
            run_record.status = "COMPLETED"
        elif workflow_type == "PR_REVIEW":
            output_md = run_pr_reviewer_workflow(repo_name, 1, mcp_tools, tracer, memory)
            run_record.status = "COMPLETED"
        elif workflow_type == "TEST_GENERATION":
            output_md = run_test_generator_workflow(repo_name, user_prompt, mcp_tools, tracer, memory)
            run_record.status = "COMPLETED"
        elif workflow_type == "SECURITY_AUDIT":
            output_md = run_security_auditor_workflow(repo_name, mcp_tools, tracer, memory)
            run_record.status = "COMPLETED"
        elif workflow_type == "FULL_ENGINEERING_WORKFLOW":
            agent_state = AgentState(user_request=user_prompt, repo_name=repo_name, branch=branch)
            updated_state = prepare_engineering_fix_stateful(agent_state, mcp_tools, tracer, memory)
            
            run_record.status = updated_state.current_state.value
            run_record.branch_name = updated_state.branch_name

            # Create Approval record if WAITING_FOR_APPROVAL
            if updated_state.current_state == WorkflowState.WAITING_FOR_APPROVAL:
                app_rec = Approval(
                    id=f"APP-{run_id}",
                    run_id=run_id,
                    user_id=run_record.user_id,
                    action_type="CREATE_SAFE_BRANCH_AND_PR",
                    repo_name=repo_name,
                    target_branch=updated_state.branch_name,
                    change_summary=f"Resolved issue '{user_prompt}' via multi-agent stateful workflow.",
                    status="PENDING",
                    payload_json={
                        "target_path": list(updated_state.proposed_changes.keys())[0],
                        "modified_content": list(updated_state.proposed_changes.values())[0],
                        "test_filename": list(updated_state.generated_tests.keys())[0],
                        "test_code": list(updated_state.generated_tests.values())[0],
                        "branch_name": updated_state.branch_name,
                        "base_branch": branch,
                        "issue_title": user_prompt
                    }
                )
                db.add(app_rec)
                asyncio.run(ws_manager.broadcast_run_event(run_id, "approval.required", {"approval_id": app_rec.id}))

            output_md = f"Prepared engineering fix for '{user_prompt}'. State: {updated_state.current_state.value}"

        # Persist steps to database
        for step in tracer.steps:
            db.add(AgentStep(
                run_id=run_id,
                agent_name=step["agent"],
                action=step["action"],
                tool_name=step.get("tool"),
                duration_sec=step.get("duration_sec", 0.0) or 0.0,
                status="SUCCESS" if not step.get("error") else "FAILED"
            ))

        run_record.duration_sec = round(time.time() - tracer.start_time, 2)
        run_record.updated_at = time.time()
        db.commit()

        # Broadcast run.completed
        asyncio.run(ws_manager.broadcast_run_event(run_id, "run.completed", {"status": run_record.status, "duration": run_record.duration_sec}))

    except Exception as e:
        run_record.status = "FAILED"
        run_record.updated_at = time.time()
        db.commit()
        asyncio.run(ws_manager.broadcast_run_event(run_id, "run.failed", {"error": str(e)}))
    finally:
        db.close()
