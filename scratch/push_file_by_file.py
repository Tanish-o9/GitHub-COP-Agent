"""
Script to stage and commit files one-by-one with descriptive commit messages.
"""
import os
import subprocess

files_to_commit = [
    # 1. Config & Docs
    (".gitignore", "chore: add .gitignore file"),
    ("requirements.txt", "chore: add production requirements.txt dependencies"),
    ("README.md", "docs: add comprehensive platform README and architecture documentation"),
    ("Dockerfile", "infra: add multi-stage Dockerfile for containerization"),
    ("docker-compose.yml", "infra: add docker-compose service configuration"),
    (".env.example", "config: add environment variable template example"),

    # 2. Base MCP & Core Infrastructure
    ("github_mcp.py", "feat(mcp): add GitHub MCP Tool abstraction layer with local fallbacks"),
    ("agent_tracer.py", "feat(observability): add AgentTracer for execution tracking and secret sanitization"),
    ("agent_state.py", "feat(workflow): add AgentState and stateful workflow transition definitions"),
    ("repo_memory.py", "feat(memory): add version-aware durable repository memory"),
    ("repo_cache.py", "feat(cache): add in-memory repository structure caching"),
    ("human_approval.py", "feat(security): add HumanApprovalRequest checkpoint engine"),
    ("security_gate.py", "feat(security): add SecurityGate vulnerability patch auditing"),
    ("rag_engine.py", "feat(rag): add CodebaseRAGEngine hybrid semantic and keyword retrieval"),
    ("dependency_analyzer.py", "feat(analysis): add DependencyAnalyzer change impact detection"),
    ("context_builder.py", "feat(rag): add SmartContextBuilder focused context synthesizer"),
    ("event_router.py", "feat(events): add EventRouter GitHub webhook triage module"),
    ("health_check.py", "feat(ops): add HealthCheckManager system diagnostics module"),
    ("evidence_checker.py", "feat(security): add EvidenceChecker hallucination validation guard"),
    ("prompt_injection_guard.py", "feat(security): add PromptInjectionGuard untrusted input sanitizer"),
    ("idempotency_guard.py", "feat(security): add IdempotencyGuard mutation guard"),
    ("state_validator.py", "feat(security): add StateValidator state transition integrity validator"),
    ("report_generator.py", "feat(reporting): add ReportGenerator benchmark exporter"),

    # 3. Database Layer
    ("database/__init__.py", "chore(db): initialize database package"),
    ("database/connection.py", "feat(db): add SQLAlchemy connection session setup"),
    ("database/models.py", "feat(db): add ORM models for users, runs, webhooks, approvals, and outcomes"),

    # 4. Worker & Scale Infrastructure
    ("worker/__init__.py", "chore(worker): initialize worker package"),
    ("worker/task_queue.py", "feat(worker): add Redis task queue and distributed locks"),
    ("worker/worker_main.py", "feat(worker): add async background task execution worker"),
    ("checkpoint_manager.py", "feat(durable): add CheckpointManager workflow state persistence"),
    ("scheduler.py", "feat(scheduler): add ResourceScheduler concurrency limits and quota manager"),
    ("retry_handler.py", "feat(resilience): add RetryHandler exponential backoff execution handler"),
    ("dead_letter.py", "feat(resilience): add DeadLetterQueue task failure recovery queue"),
    ("incremental_rag.py", "feat(rag): add IncrementalRAGIndexer code symbol change indexer"),
    ("pr_tracker.py", "feat(pr): add PRTracker background reconciliation engine"),
    ("cost_budget.py", "feat(budget): add CostBudgetManager token and concurrency budget controller"),
    ("mcp_lifecycle.py", "feat(mcp): add MCPConnectionPool lifecycle manager"),

    # 5. Agents
    ("agents/__init__.py", "chore(agents): initialize agents package"),
    ("agents/manager_agent.py", "feat(agents): add ManagerAgent request classification and routing"),
    ("agents/researcher_agent.py", "feat(agents): add ResearcherAgent context discovery engine"),
    ("agents/analyzer_agent.py", "feat(agents): add AnalyzerAgent root cause and architecture analyzer"),
    ("agents/coder_agent.py", "feat(agents): add CoderAgent patch and implementation planner"),
    ("agents/test_agent.py", "feat(agents): add TestAgent test generator and runner"),
    ("agents/reviewer_agent.py", "feat(agents): add ReviewerAgent patch reviewer"),

    # 6. Workflows
    ("workflows/__init__.py", "chore(workflows): initialize workflows package"),
    ("workflows/repo_intelligence.py", "feat(workflows): add Repository Intelligence stateful workflow"),
    ("workflows/issue_analyzer.py", "feat(workflows): add Issue Analyzer workflow"),
    ("workflows/pr_reviewer.py", "feat(workflows): add PR Reviewer workflow"),
    ("workflows/test_generator.py", "feat(workflows): add Test Generator workflow"),
    ("workflows/security_auditor.py", "feat(workflows): add Security Auditor workflow"),
    ("workflows/change_impact.py", "feat(workflows): add Change Impact Analysis workflow"),
    ("workflows/engineering_workflow.py", "feat(workflows): add End-to-End Stateful Engineering Fix workflow"),

    # 7. Code Intelligence (Phase 7)
    ("code_parser.py", "feat(intelligence): add Python AST code parser"),
    ("code_graph.py", "feat(intelligence): add CodeIntelligenceGraph symbol linkage graph"),
    ("retrieval_reranker.py", "feat(intelligence): add RAG 2.0 hybrid reranker and context compressor"),
    ("semantic_diff.py", "feat(intelligence): add SemanticDiffAnalyzer AST diff parser"),
    ("risk_engine.py", "feat(intelligence): add ChangeRiskEngine risk scoring engine"),
    ("test_impact.py", "feat(intelligence): add TestImpactAnalyzer test suite selector"),
    ("agent_registry.py", "feat(intelligence): add SpecialistAgentRegistry capabilities manager"),
    ("self_verifier.py", "feat(intelligence): add SelfVerifierCritic patch critic system"),
    ("patch_quality.py", "feat(intelligence): add PatchQualityEvaluator patch quality scorer"),
    ("issue_similarity.py", "feat(intelligence): add IssueSimilarityEngine duplicate issue clusterer"),
    ("engineering_memory_v2.py", "feat(intelligence): add EngineeringMemoryV2 long-term memory engine"),
    ("architecture_explainer.py", "feat(intelligence): add ArchitectureExplainer system view generator"),

    # 8. Autonomous Engineering (Phase 8)
    ("autonomy_policy.py", "feat(autonomy): add AutonomyPolicyManager bounded autonomy levels 0-4"),
    ("engineering_contract.py", "feat(autonomy): add TaskContractValidator task contract validator"),
    ("autonomy_safety.py", "feat(autonomy): add AutonomySafetyEvaluator risk gating evaluator"),
    ("acceptance_engine.py", "feat(autonomy): add AcceptanceEngine criteria verification engine"),
    ("plan_validator.py", "feat(autonomy): add PlanValidator implementation approach formulator"),
    ("patch_optimizer.py", "feat(autonomy): add PatchOptimizer scope discipline optimizer"),
    ("feedback_engine.py", "feat(autonomy): add FeedbackEngine CI and PR feedback classifier"),
    ("ci_failure_analyzer.py", "feat(autonomy): add CIFailureAnalyzer stack trace parser"),
    ("root_cause.py", "feat(autonomy): add RootCauseEngine diagnostic hypothesis generator"),
    ("merge_conflict.py", "feat(autonomy): add MergeConflictAnalyzer conflict analyzer"),
    ("regression_engine.py", "feat(autonomy): add RegressionRiskPredictor regression risk estimator"),
    ("test_selector.py", "feat(autonomy): add AdaptiveTestSelector execution mode selector"),
    ("post_merge.py", "feat(autonomy): add PostMergeValidator post-merge cache invalidator"),
    ("engineering_outcome_memory.py", "feat(autonomy): add EngineeringOutcomeMemory outcome knowledge store"),
    ("autonomous_engine.py", "feat(autonomy): add AutonomousEngineeringController bounded engineering engine"),

    # 9. API REST Gateway
    ("api/__init__.py", "chore(api): initialize API package"),
    ("api/auth.py", "feat(api): add JWT authentication and tenant isolation middleware"),
    ("api/websocket.py", "feat(api): add WebSocket real-time progress broadcast manager"),
    ("api/routes_runs.py", "feat(api): add REST endpoints for agent runs"),
    ("api/routes_approvals.py", "feat(api): add REST endpoints for human approval checkpoints"),
    ("api/routes_webhooks.py", "feat(api): add production GitHub webhook listener endpoint"),
    ("api/routes_ops.py", "feat(api): add REST endpoints for cloud operations dashboard"),
    ("api/routes_intelligence.py", "feat(api): add REST endpoints for codebase intelligence"),
    ("api/routes_engineering.py", "feat(api): add REST endpoints for autonomous engineering tasks"),
    ("api/routes_evals.py", "feat(api): add REST endpoints for evaluation benchmark metrics"),
    ("api/main.py", "feat(api): add FastAPI application entrypoint with routes mounting"),

    # 10. UIs & Test Suites
    ("chat_github.py", "feat(ui): add Chat with GitHub entrypoint"),
    ("chat_github_llama3.py", "feat(ui): add Ollama Llama-3 integration interface"),
    ("cli.py", "feat(cli): add interactive Terminal CLI entrypoint"),
    ("app.py", "feat(ui): add GitHub Cop Agent Streamlit multi-tab operations workspace"),
    ("eval/__init__.py", "chore(eval): initialize evaluation package"),
    ("eval/golden_dataset.json", "test(eval): add golden evaluation dataset benchmarks"),
    ("eval/eval_runner.py", "test(eval): add EvaluationRunner golden dataset test execution runner"),
    ("eval/load_test_runner.py", "test(eval): add LoadTestRunner concurrent load testing benchmark"),
    ("scratch/test_phase2.py", "test: add Phase 2 stateful workflow integration test suite"),
    ("scratch/test_phase3.py", "test: add Phase 3 RAG and memory integration test suite"),
    ("scratch/test_phase4.py", "test: add Phase 4 evaluation and security hardening test suite"),
    ("scratch/test_phase5.py", "test: add Phase 5 FastAPI and worker integration test suite"),
    ("scratch/test_phase6.py", "test: add Phase 6 durability and concurrency test suite"),
    ("scratch/test_phase7.py", "test: add Phase 7 code intelligence graph test suite"),
    ("scratch/test_phase8.py", "test: add Phase 8 autonomous engineering integration test suite")
]

def main():
    committed_count = 0
    for rel_path, msg in files_to_commit:
        if os.path.exists(rel_path):
            print(f"[{committed_count + 1}/{len(files_to_commit)}] Staging '{rel_path}'...")
            subprocess.run(["git", "add", rel_path], check=True)
            res = subprocess.run(["git", "commit", "-m", msg], capture_output=True, text=True)
            if res.returncode == 0:
                committed_count += 1
                print(f"  [OK] Committed: {msg}")
            else:
                print(f"  - Skip/No change: {res.stdout or res.stderr}")
        else:
            print(f"  - File not found: {rel_path}")

    print(f"\n✅ Total File-by-File Commits Created: {committed_count}")

if __name__ == "__main__":
    main()
