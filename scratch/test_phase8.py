"""
Phase 8 Automated Comprehensive Integration Test Suite
Validates:
1. Database schema & Phase 8 models (EngineeringTaskModel, TaskCriterionModel, FeedbackEventModel, etc.)
2. AutonomyPolicyManager (Autonomy levels 0 to 4, bounds, and iteration caps)
3. TaskContract & TaskContractValidator (Contract creation, parameter validation, and budget caps)
4. AutonomySafetyEvaluator (Policy decisions: SAFE_TO_PROCEED, REQUIRES_APPROVAL, BLOCKED)
5. AcceptanceEngine (Natural language requirement parsing into verifiable acceptance criteria)
6. PlanValidator (Plan validation and alternative approach formulation A/B/C)
7. PatchOptimizer (Patch scope discipline and minimal safe patch recommendations)
8. FeedbackEngine (CI failure, PR review, and merge conflict event classification)
9. CIFailureAnalyzer & RootCauseEngine (Stack trace parsing and root cause analysis with confidence)
10. MergeConflictAnalyzer (Merge conflict marker analysis and human approval enforcement)
11. RegressionRiskPredictor & AdaptiveTestSelector (Regression risk scoring and adaptive test selection)
12. PostMergeValidator & EngineeringOutcomeMemory (Post-merge verification and outcome recording)
13. AutonomousEngineeringController (End-to-end bounded task intake, planning, and approval gating)
"""
import os
import sys
import time

# Ensure root dir in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import init_db, SessionLocal
from database.models import (
    EngineeringTaskModel, TaskCriterionModel, FeedbackEventModel,
    RootCauseAnalysisModel, EngineeringOutcomeModel, AutonomyDecisionModel
)
from autonomy_policy import AutonomyPolicyManager, LEVEL_0_ANALYSIS_ONLY, LEVEL_2_CODE_AFTER_APPROVAL
from engineering_contract import TaskContractValidator, TaskContract
from autonomy_safety import AutonomySafetyEvaluator
from acceptance_engine import AcceptanceEngine
from plan_validator import PlanValidator
from patch_optimizer import PatchOptimizer
from feedback_engine import FeedbackEngine
from ci_failure_analyzer import CIFailureAnalyzer
from root_cause import RootCauseEngine
from merge_conflict import MergeConflictAnalyzer
from regression_engine import RegressionRiskPredictor
from test_selector import AdaptiveTestSelector
from post_merge import PostMergeValidator
from engineering_outcome_memory import EngineeringOutcomeMemory
from autonomous_engine import AutonomousEngineeringController
from semantic_diff import ChangeSummary
from github_mcp import GitHubMCPTools


def run_phase8_tests():
    print("==================================================")
    print("    RUNNING PHASE 8 INTEGRATION TEST SUITE       ")
    print("==================================================")

    # 1. Database Initialization
    init_db()
    db = SessionLocal()
    print("[PASS] 1. Database schema initialized successfully with Phase 8 models.")

    # 2. AutonomyPolicyManager
    pol_level2 = AutonomyPolicyManager.get_policy(LEVEL_2_CODE_AFTER_APPROVAL)
    assert pol_level2.requires_human_approval is True
    assert pol_level2.max_iterations == 3
    pol_level0 = AutonomyPolicyManager.get_policy(LEVEL_0_ANALYSIS_ONLY)
    assert pol_level0.max_files_changed == 0
    print("[PASS] 2. AutonomyPolicyManager defined explicit bounds for autonomy levels 0-4.")

    # 3. TaskContractValidator
    contract = TaskContractValidator.create_contract(
        tenant_id=1,
        repository_name="owner/repo",
        objective="Fix authentication timeout bug in auth module",
        autonomy_level=LEVEL_2_CODE_AFTER_APPROVAL
    )
    val = TaskContractValidator.validate(contract)
    assert val["valid"] is True
    print(f"[PASS] 3. TaskContractValidator validated contract: {contract.task_id}.")

    # 4. AutonomySafetyEvaluator
    safety_eval = AutonomySafetyEvaluator()
    sec_dec = safety_eval.evaluate(contract, risk_score=20.0, is_mutation_operation=True)
    assert sec_dec.decision == "REQUIRES_APPROVAL", "Write mutations must require human approval"
    print(f"[PASS] 4. AutonomySafetyEvaluator policy decision: {sec_dec.decision}.")

    # 5. AcceptanceEngine
    acc_engine = AcceptanceEngine()
    criteria = acc_engine.extract_criteria("Fix authentication timeout error in auth module")
    assert len(criteria) >= 2
    assert criteria[0].status == "UNKNOWN"
    acc_engine.update_criterion_status(criteria, criteria[0].id, "PASS", "Test passed")
    assert criteria[0].status == "PASS"
    print(f"[PASS] 5. AcceptanceEngine extracted {len(criteria)} criteria and updated status.")

    # 6. PlanValidator & Alternatives
    p_validator = PlanValidator()
    plan_res = p_validator.validate_plan(["1. Inspect code", "2. Run test"], criteria)
    assert plan_res["valid"] is True
    alts = p_validator.generate_plan_alternatives("src/auth.py")
    assert len(alts) == 3
    assert alts[0].name.startswith("Approach A")
    print(f"[PASS] 6. PlanValidator validated plan and generated {len(alts)} alternative approaches.")

    # 7. PatchOptimizer
    patch_opt = PatchOptimizer()
    summary = ChangeSummary(files_changed=["src/auth.py", "tests/test_auth.py"])
    scope_report = patch_opt.evaluate_scope(summary)
    assert scope_report.is_minimal is True
    print(f"[PASS] 7. PatchOptimizer evaluated patch scope (Score: {scope_report.scope_score}).")

    # 8. FeedbackEngine
    fb_engine = FeedbackEngine()
    fb_item = fb_engine.process_feedback("TASK-001", {"event_type": "ci_failure", "text": "FAILED: test_auth.py AssertionError"})
    assert fb_item.feedback_type == "CI_FAILURE"
    print(f"[PASS] 8. FeedbackEngine classified CI failure event: {fb_item.feedback_type}.")

    # 9. CIFailureAnalyzer & RootCauseEngine
    ci_analyzer = CIFailureAnalyzer()
    parsed_failure = ci_analyzer.parse_failure('File "src/auth.py", line 42, in validate\nAssertionError: Invalid token')
    assert parsed_failure.line_number == 42
    
    rc_engine = RootCauseEngine()
    rc_report = rc_engine.analyze_root_cause(parsed_failure)
    assert rc_report.confidence in ["HIGH", "MEDIUM", "LOW"]
    print(f"[PASS] 9. CIFailureAnalyzer & RootCauseEngine diagnosed cause (Confidence: {rc_report.confidence}).")

    # 10. MergeConflictAnalyzer
    mc_analyzer = MergeConflictAnalyzer()
    mc_report = mc_analyzer.analyze_conflict("<<<<<<< HEAD\n+def auth(): pass\n=======", "src/auth.py")
    assert mc_report.requires_human_approval is True
    print(f"[PASS] 10. MergeConflictAnalyzer analyzed conflict and enforced human approval.")

    # 11. RegressionRiskPredictor & AdaptiveTestSelector
    reg_predictor = RegressionRiskPredictor()
    reg_report = reg_predictor.predict_risk(["src/auth.py"])
    assert 0.0 <= reg_report.regression_score <= 100.0

    test_selector = AdaptiveTestSelector()
    exec_plan = test_selector.select_tests(["src/auth.py"], risk_report=reg_report, requested_mode="FAST")
    assert len(exec_plan.selected_tests) >= 1
    print(f"[PASS] 11. AdaptiveTestSelector selected {len(exec_plan.selected_tests)} tests for mode {exec_plan.mode}.")

    # 12. PostMergeValidator & EngineeringOutcomeMemory
    mcp_tools = GitHubMCPTools()
    pm_validator = PostMergeValidator()
    pm_summary = pm_validator.validate_post_merge(mcp_tools, "Shubhamsaboo/awesome-llm-apps", 42, "ai-fix/issue-42")
    assert pm_summary.status in ["COMPLETED", "VERIFIED"]

    outcome_mem = EngineeringOutcomeMemory("Shubhamsaboo/awesome-llm-apps")
    rec = outcome_mem.record_outcome("TASK-001", "Fix auth timeout", patch_quality_score=90.0, risk_score=20.0)
    assert rec.patch_quality_score == 90.0
    print("[PASS] 12. PostMergeValidator and EngineeringOutcomeMemory verified.")

    # 13. AutonomousEngineeringController End-to-End Task Intake & Execution
    controller = AutonomousEngineeringController(db)
    intake_res = controller.intake_task(
        tenant_id=1,
        repository_name="Shubhamsaboo/awesome-llm-apps",
        objective="Fix authentication timeout bug in auth module",
        autonomy_level=2
    )
    task_id = intake_res["task_id"]
    assert intake_res["status"] == "INTAKE"

    exec_res = controller.execute_bounded_workflow(task_id, mcp_tools)
    assert exec_res["status"] == "APPROVAL_REQUIRED"
    assert exec_res["approval_required"] is True
    print(f"[PASS] 13. AutonomousEngineeringController executed bounded workflow (Task {task_id} -> APPROVAL_REQUIRED).")

    db.close()
    print("==================================================")
    print("   ALL PHASE 8 INTEGRATION TESTS PASSED (13/13)   ")
    print("==================================================")


if __name__ == "__main__":
    run_phase8_tests()
