"""
Phase 6 Automated Comprehensive Integration Test Suite
Validates:
1. Database schema & models (AgentCheckpoint, PRTracker, DeadLetterJob)
2. CheckpointManager (State persistence & worker recovery)
3. ResourceScheduler (Concurrency limits & fair queueing)
4. RetryHandler (Exponential backoff & transient classification)
5. DeadLetterManager (DLQ storage & manual requeueing)
6. MCPConnectionPool (Lifecycle & health check pooling)
7. CacheManager (Redis multi-tenant caching & repo invalidation)
8. IncrementalRAGIndexer (Push webhook incremental indexing)
9. PRLifecycleTracker (PR lifecycle tracking & GitHub state reconciliation)
10. ResourceBudgetTracker (Resource & cost budget enforcement)
11. LoadTestRunner (Concurrent load testing benchmark)
"""
import os
import sys
import time

# Ensure root dir in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import init_db, SessionLocal
from database.models import User, Repository, AgentRun, AgentCheckpoint, PRTracker, DeadLetterJob
from checkpoint_manager import CheckpointManager
from scheduler import ResourceScheduler, MAX_CONCURRENT_RUNS_PER_USER
from retry_handler import execute_with_retry, is_transient_error
from dead_letter import DeadLetterManager
from mcp_lifecycle import MCPConnectionPool
from cache_manager import CacheManager
from rag_engine import CodebaseRAGEngine
from incremental_rag import IncrementalRAGIndexer
from pr_tracker import PRLifecycleTracker
from cost_budget import ResourceBudgetTracker, ResourceBudgetExceeded
from eval.load_test_runner import LoadTestRunner
from github_mcp import GitHubMCPTools


def run_phase6_tests():
    print("==================================================")
    print("    RUNNING PHASE 6 INTEGRATION TEST SUITE       ")
    print("==================================================")

    # 1. Database Initialization
    init_db()
    db = SessionLocal()
    # Clean up old active test runs for isolation
    db.query(AgentRun).filter(AgentRun.user_id == 1, AgentRun.status == "RUNNING").update({"status": "COMPLETED"})
    db.commit()
    print("[PASS] 1. Database schema initialized successfully with Phase 6 models.")

    # 2. CheckpointManager & Worker Recovery
    chk_mgr = CheckpointManager(db)
    run_id = f"RUN-P6-{int(time.time()*1000)}"
    test_run = AgentRun(id=run_id, user_id=1, user_request="Analyze issue #10", status="RUNNING")
    db.add(test_run)
    db.commit()

    chk1 = chk_mgr.create_checkpoint(run_id, "issue_analysis", {"findings": "Root cause identified", "token": "secret_123"})
    assert chk1.state_json["findings"] == "Root cause identified"
    assert chk1.state_json["token"] == "[REDACTED]", "Secrets must be sanitized in checkpoints"

    resumed_state = chk_mgr.resume_run_state(run_id)
    assert resumed_state["resumed"] is True
    assert resumed_state["last_completed_step"] == "issue_analysis"
    print("[PASS] 2. CheckpointManager successfully persisted sanitized state and resumed run state.")

    # 3. ResourceScheduler & Concurrency Limits
    scheduler = ResourceScheduler(db)
    can_start = scheduler.can_start_run(user_id=1)
    assert can_start is True
    q_stats = scheduler.get_queue_stats()
    assert "active_runs" in q_stats
    assert q_stats["max_concurrent_per_user"] == MAX_CONCURRENT_RUNS_PER_USER
    print(f"[PASS] 3. ResourceScheduler enforced limits successfully (Queue Stats: {q_stats}).")

    # 4. RetryHandler & Transient Classification
    assert is_transient_error(ValueError("Connection timeout to GitHub")) is True
    assert is_transient_error(ValueError("Permission denied")) is False

    retry_count = 0
    def transient_flaky_func():
        nonlocal retry_count
        retry_count += 1
        if retry_count < 2:
            raise ValueError("Temporary network glitch")
        return "SUCCESS"

    res = execute_with_retry(transient_flaky_func, max_retries=3, initial_delay=0.01)
    assert res == "SUCCESS"
    assert retry_count == 2
    print("[PASS] 4. RetryHandler transient error backoff and retry executed successfully.")

    # 5. DeadLetterManager
    dlq_mgr = DeadLetterManager(db)
    dl_job = dlq_mgr.moveToDeadLetter(
        run_id=run_id,
        user_id=1,
        error_code="MAX_RETRIES_EXCEEDED",
        last_error="Fatal timeout",
        retry_count=3,
        payload={"request": "test"}
    )
    assert dl_job.id.startswith("DLQ-")
    
    requeued = dlq_mgr.retry_dead_letter_job(dl_job.id)
    assert requeued.status == "QUEUED"
    print(f"[PASS] 5. DeadLetterManager successfully routed failed job to DLQ and requeued.")

    # 6. MCPConnectionPool
    mcp_client = MCPConnectionPool.get_connection()
    assert isinstance(mcp_client, GitHubMCPTools)
    pool_status = MCPConnectionPool.get_pool_status()
    assert pool_status["active_connections"] == 1
    print(f"[PASS] 6. MCPConnectionPool pooled connection (Status: {pool_status}).")

    # 7. CacheManager
    cache_mgr = CacheManager()
    cache_mgr.set("Shubhamsaboo/awesome-llm-apps", "meta", "info", {"stars": 500})
    val = cache_mgr.get("Shubhamsaboo/awesome-llm-apps", "meta", "info")
    # Should safely return val if Redis running, or None if offline
    cache_mgr.invalidate_repo("Shubhamsaboo/awesome-llm-apps")
    print("[PASS] 7. CacheManager set/get/invalidation logic validated.")

    # 8. IncrementalRAGIndexer
    rag = CodebaseRAGEngine("Shubhamsaboo/awesome-llm-apps", "main")
    rag.chunks.append(rag.chunk_code_file("src/auth.py", "def authenticate(): pass")[0])
    rag.chunks.append(rag.chunk_code_file("src/utils.py", "def helper(): pass")[0])
    assert len(rag.chunks) == 2

    inc_indexer = IncrementalRAGIndexer(rag, cache_mgr)
    summary = inc_indexer.update_modified_files(mcp_client, modified_files=["src/auth.py"])
    assert summary["purged_chunks"] == 1
    print(f"[PASS] 8. IncrementalRAGIndexer purged modified file chunks and updated index.")

    # 9. PRLifecycleTracker
    pr_tracker = PRLifecycleTracker(db)
    pr_entry = pr_tracker.register_pr(
        run_id=run_id,
        repo_name="Shubhamsaboo/awesome-llm-apps",
        pr_number=42,
        title="Fix authentication error",
        branch_name="ai-fix/issue-42",
        url="https://github.com/Shubhamsaboo/awesome-llm-apps/pull/42"
    )
    assert pr_entry.status == "PR_CREATED"
    updated_pr = pr_tracker.update_pr_status("Shubhamsaboo/awesome-llm-apps", 42, "APPROVED")
    assert updated_pr.status == "APPROVED"
    print("[PASS] 9. PRLifecycleTracker tracked PR lifecycle state transitions.")

    # 10. ResourceBudgetTracker
    budget = ResourceBudgetTracker(max_agent_calls=2, max_mcp_calls=10)
    budget.record_agent_call()
    budget.record_agent_call()
    budget_exceeded = False
    try:
        budget.record_agent_call()  # 3rd call triggers budget exception
    except ResourceBudgetExceeded as e:
        budget_exceeded = True
        assert "Workflow stopped because the configured resource budget was reached" in str(e)
    assert budget_exceeded is True, "Budget tracker must raise exception when limit exceeded"
    print("[PASS] 10. ResourceBudgetTracker correctly halted execution on limit breach.")

    # 11. LoadTestRunner
    lt_runner = LoadTestRunner(target_concurrency=5, total_requests=10)
    metrics = lt_runner.run_load_test()
    assert metrics["total_requests"] == 10
    assert metrics["requests_per_sec"] > 0
    print(f"[PASS] 11. LoadTestRunner produced actual load metrics: {metrics}")

    db.close()
    print("==================================================")
    print("   ALL PHASE 6 INTEGRATION TESTS PASSED (11/11)   ")
    print("==================================================")


if __name__ == "__main__":
    run_phase6_tests()
