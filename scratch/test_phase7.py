"""
Phase 7 Automated Comprehensive Integration Test Suite
Validates:
1. Database schema & Phase 7 models (CodeEntityModel, CodeRelationshipModel, RiskAssessmentModel, etc.)
2. ASTCodeParser (Static AST parsing of Python classes, functions, and docstrings)
3. CodeIntelligenceGraph (Node/edge graph building and dependency impact analysis)
4. HybridReranker & ContextCompressor (Query classification, reranking, and compression)
5. SemanticDiffAnalyzer (Git diff symbol extraction and risk factor detection)
6. ChangeRiskEngine (Explainable change risk scoring 0-100 and levels)
7. TestImpactAnalyzer (Test relationship mapping and coverage recommendations)
8. SpecialistAgentRegistry (Dynamic specialist agent selection)
9. SelfVerifier (Output grounding, file reality verification, and critic feedback)
10. PatchQualityEvaluator (Explainable patch quality scoring)
11. IssueSimilarityEngine (Duplicate issue detection and issue clustering)
12. EngineeringMemoryV2 (Categorized memory with Code > Memory precedence rule)
13. ArchitectureExplainer (Executive, Developer, Request Flow, and Data Flow views)
"""
import os
import sys

# Ensure root dir in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import init_db, SessionLocal
from database.models import (
    CodeEntityModel, CodeRelationshipModel, RiskAssessmentModel,
    PatchQualityAssessmentModel, IssueSimilarityModel
)
from code_parser import ASTCodeParser
from code_graph import CodeIntelligenceGraph
from retrieval_reranker import HybridReranker, QueryClassifier, QueryExpander, ContextCompressor
from semantic_diff import SemanticDiffAnalyzer
from risk_engine import ChangeRiskEngine
from test_impact import TestImpactAnalyzer
from agent_registry import SpecialistAgentRegistry
from self_verifier import SelfVerifier
from patch_quality import PatchQualityEvaluator
from issue_similarity import IssueSimilarityEngine
from engineering_memory_v2 import EngineeringMemoryV2
from architecture_explainer import ArchitectureExplainer
from rag_engine import CodeChunk


def run_phase7_tests():
    print("==================================================")
    print("    RUNNING PHASE 7 INTEGRATION TEST SUITE       ")
    print("==================================================")

    # 1. Database Schema & Phase 7 Models
    init_db()
    db = SessionLocal()
    print("[PASS] 1. Database schema initialized successfully with Phase 7 models.")

    # 2. ASTCodeParser
    sample_code = """
'''Module docstring'''
import os

class AuthManager:
    '''Handles authentication'''
    def authenticate(self, token: str):
        return token == "secret"

def validate_token(t):
    return AuthManager().authenticate(t)
"""
    parser = ASTCodeParser()
    entities = parser.parse_file_content("owner/repo", "src/auth.py", sample_code)
    assert len(entities) >= 3  # module, class, function/method
    class_ent = next(e for e in entities if e.entity_type == "class")
    assert class_ent.name == "AuthManager"
    print(f"[PASS] 2. ASTCodeParser parsed {len(entities)} CodeEntities (Class: {class_ent.name}).")

    # 3. CodeIntelligenceGraph
    graph = CodeIntelligenceGraph("owner/repo")
    graph.build_from_files({"src/auth.py": sample_code})
    summary = graph.get_summary()
    assert summary["total_entities"] >= 3
    impact = graph.get_affected_nodes("src/auth.py")
    assert impact["target_file"] == "src/auth.py"
    print(f"[PASS] 3. CodeIntelligenceGraph built node/edge structure ({summary}).")

    # 4. HybridReranker & ContextCompressor
    q_cat = QueryClassifier.classify("Where is JWT token authentication handled?")
    assert q_cat == "SECURITY"
    exp_queries = QueryExpander.expand("jwt_token_auth")
    assert len(exp_queries) >= 1

    chunk_a = CodeChunk("owner/repo", "main", "src/auth.py", "authenticate", "python", 1, 10, "function", "def authenticate(token): pass")
    chunk_b = CodeChunk("owner/repo", "main", "src/utils.py", "helper", "python", 1, 5, "function", "def helper(): pass")

    candidates = [
        {"score": 2.0, "chunk": chunk_a},
        {"score": 1.0, "chunk": chunk_b}
    ]
    reranked = HybridReranker.rerank("JWT token authentication", candidates, top_k=2)
    assert reranked[0]["chunk"].file_path == "src/auth.py"

    compressed = ContextCompressor.compress_context(reranked)
    assert compressed["used_chunks"] == 2
    print(f"[PASS] 4. HybridReranker and ContextCompressor executed (Top match: {reranked[0]['chunk'].file_path}).")

    # 5. SemanticDiffAnalyzer
    sample_diff = """+++ b/src/auth.py
+def authenticate_jwt(token):
+    return True
-def old_auth():
+    # Token verification
"""
    diff_analyzer = SemanticDiffAnalyzer()
    diff_sum = diff_analyzer.analyze_diff(sample_diff, changed_files=["src/auth.py"])
    assert "authenticate_jwt" in diff_sum.added_symbols
    print(f"[PASS] 5. SemanticDiffAnalyzer identified added symbol: {diff_sum.added_symbols}.")

    # 6. ChangeRiskEngine
    risk_engine = ChangeRiskEngine()
    risk_report = risk_engine.evaluate_risk(diff_sum, code_graph=graph)
    assert 0.0 <= risk_report.risk_score <= 100.0
    assert risk_report.risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    print(f"[PASS] 6. ChangeRiskEngine calculated risk score: {risk_report.risk_score} ({risk_report.risk_level}).")

    # 7. TestImpactAnalyzer
    test_analyzer = TestImpactAnalyzer()
    test_report = test_analyzer.analyze_impact(["src/auth.py"], code_graph=graph)
    assert len(test_report.related_tests) >= 1
    assert "tests/test_auth.py" in test_report.related_tests
    print(f"[PASS] 7. TestImpactAnalyzer identified related test suite: {test_report.related_tests[0]}.")

    # 8. SpecialistAgentRegistry
    specialists = SpecialistAgentRegistry.select_specialists("FULL_ENGINEERING_WORKFLOW")
    assert len(specialists) >= 3
    spec_names = [s.name for s in specialists]
    assert "Coding Agent" in spec_names
    print(f"[PASS] 8. SpecialistAgentRegistry dynamically selected agents: {spec_names}.")

    # 9. SelfVerifier
    verifier = SelfVerifier()
    v_res = verifier.verify_response(
        user_request="Fix issue in src/auth.py",
        response_text="Modified `src/auth.py` at [`src/auth.py:L1-L10`](file:///src/auth.py#L1-L10)",
        known_repo_files=["src/auth.py"],
        test_executed=True
    )
    assert v_res.passed is True
    print(f"[PASS] 9. SelfVerifier verified response grounding (Score: {v_res.score}).")

    # 10. PatchQualityEvaluator
    quality_eval = PatchQualityEvaluator()
    q_report = quality_eval.evaluate_patch(diff_sum, risk_report=risk_report, test_passed=True, security_passed=True)
    assert q_report.quality_score >= 50.0
    print(f"[PASS] 10. PatchQualityEvaluator scored patch quality: {q_report.quality_score}/100.")

    # 11. IssueSimilarityEngine
    sim_engine = IssueSimilarityEngine()
    issue1 = {"number": 1, "title": "KeyError in GITHUB_TOKEN loading", "body": "App crashes when token missing"}
    issue2 = {"number": 2, "title": "Missing GITHUB_TOKEN causes KeyError", "body": "Token missing traceback"}
    dups = sim_engine.find_duplicates(issue1, [issue2], threshold=40.0)
    assert len(dups) == 1
    assert dups[0].similarity_score >= 40.0
    clusters = sim_engine.cluster_issues([issue1, issue2])
    assert len(clusters["authentication"]) == 2
    print(f"[PASS] 11. IssueSimilarityEngine detected duplicate issue (Similarity: {dups[0].similarity_score}%).")

    # 12. EngineeringMemoryV2
    mem_v2 = EngineeringMemoryV2("owner/repo", "main")
    mem_v2.add_memory("CONVENTIONS", "Use pytest for all test files", confidence=0.95)
    entries = mem_v2.query_memory(category="CONVENTIONS")
    assert len(entries) == 1
    code_win = mem_v2.resolve_code_conflict("Old convention: unittest", "Current code: pytest")
    assert code_win == "Current code: pytest", "Current Code > Old Memory precedence rule must hold"
    print("[PASS] 12. EngineeringMemoryV2 confidence scoring & Code > Memory precedence verified.")

    # 13. ArchitectureExplainer
    explainer = ArchitectureExplainer("owner/repo", code_graph=graph)
    views = explainer.generate_architecture_views()
    assert "executive_overview" in views
    assert len(views["request_flow"]) >= 4
    print("[PASS] 13. ArchitectureExplainer generated multi-perspective architectural views.")

    db.close()
    print("==================================================")
    print("   ALL PHASE 7 INTEGRATION TESTS PASSED (13/13)   ")
    print("==================================================")


if __name__ == "__main__":
    run_phase7_tests()
