"""
Repository Intelligence REST API Routes
Provides architecture views, code graph inspection, semantic code search, semantic diff analysis, risk scoring, and test impact intelligence.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User
from api.auth import get_current_user
from mcp_lifecycle import MCPConnectionPool
from code_graph import CodeIntelligenceGraph
from architecture_explainer import ArchitectureExplainer
from semantic_diff import SemanticDiffAnalyzer
from risk_engine import ChangeRiskEngine
from test_impact import TestImpactAnalyzer
from issue_similarity import IssueSimilarityEngine
from retrieval_reranker import HybridReranker, QueryClassifier
from rag_engine import CodebaseRAGEngine

router = APIRouter(prefix="/api/v1/intelligence", tags=["Repository Intelligence"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class DiffRequest(BaseModel):
    diff_text: str
    changed_files: List[str] = []


class TestImpactRequest(BaseModel):
    changed_files: List[str]


class DuplicateCheckRequest(BaseModel):
    target_issue: Dict[str, Any]
    existing_issues: List[Dict[str, Any]] = []


@router.get("/repository/{repo_owner}/{repo_name}/architecture")
def get_repository_architecture(
    repo_owner: str,
    repo_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch multi-view architecture documentation for a repository."""
    full_repo = f"{repo_owner}/{repo_name}"
    explainer = ArchitectureExplainer(full_repo)
    mcp_tools = MCPConnectionPool.get_connection()
    return explainer.generate_architecture_views(mcp_tools)


@router.get("/repository/{repo_owner}/{repo_name}/graph")
def get_repository_graph(
    repo_owner: str,
    repo_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch code graph summary metrics."""
    full_repo = f"{repo_owner}/{repo_name}"
    graph = CodeIntelligenceGraph(full_repo)
    return graph.get_summary()


@router.post("/repository/{repo_owner}/{repo_name}/search")
def semantic_code_search(
    repo_owner: str,
    repo_name: str,
    req: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute engineering-aware hybrid RAG search with reranking."""
    full_repo = f"{repo_owner}/{repo_name}"
    mcp_tools = MCPConnectionPool.get_connection()
    rag = CodebaseRAGEngine(full_repo)
    raw_results = rag.hybrid_search(req.query, top_k=req.top_k * 2)
    reranked = HybridReranker.rerank(req.query, raw_results, top_k=req.top_k)

    return {
        "query": req.query,
        "category": QueryClassifier.classify(req.query),
        "results_count": len(reranked),
        "results": [
            {
                "score": r["score"],
                "citation": r["citation"],
                "symbol": r["chunk"].symbol_name,
                "file_path": r["chunk"].file_path,
                "line_range": f"L{r['chunk'].start_line}-L{r['chunk'].end_line}",
                "content": r["chunk"].content[:300]
            }
            for r in reranked
        ]
    }


@router.post("/repository/{repo_owner}/{repo_name}/analyze-diff")
def analyze_semantic_diff(
    repo_owner: str,
    repo_name: str,
    req: DiffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze a Git diff to extract symbol modifications and risk factors."""
    analyzer = SemanticDiffAnalyzer()
    summary = analyzer.analyze_diff(req.diff_text, changed_files=req.changed_files)
    return summary.to_dict()


@router.post("/repository/{repo_owner}/{repo_name}/risk")
def calculate_change_risk(
    repo_owner: str,
    repo_name: str,
    req: DiffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate an explainable change risk score and level."""
    full_repo = f"{repo_owner}/{repo_name}"
    analyzer = SemanticDiffAnalyzer()
    summary = analyzer.analyze_diff(req.diff_text, changed_files=req.changed_files)
    
    graph = CodeIntelligenceGraph(full_repo)
    risk_engine = ChangeRiskEngine()
    report = risk_engine.evaluate_risk(summary, code_graph=graph)
    return report.to_dict()


@router.post("/repository/{repo_owner}/{repo_name}/test-impact")
def analyze_test_impact(
    repo_owner: str,
    repo_name: str,
    req: TestImpactRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Identify affected test suites and missing coverage areas for changed files."""
    full_repo = f"{repo_owner}/{repo_name}"
    graph = CodeIntelligenceGraph(full_repo)
    impact_analyzer = TestImpactAnalyzer()
    report = impact_analyzer.analyze_impact(req.changed_files, code_graph=graph)
    return report.to_dict()


@router.post("/repository/{repo_owner}/{repo_name}/duplicate-issues")
def check_duplicate_issues(
    repo_owner: str,
    repo_name: str,
    req: DuplicateCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detect candidate duplicate issues and cluster repository issues."""
    sim_engine = IssueSimilarityEngine()
    duplicates = sim_engine.find_duplicates(req.target_issue, req.existing_issues)
    clusters = sim_engine.cluster_issues(req.existing_issues)

    return {
        "duplicates_found": len(duplicates),
        "candidates": [d.to_dict() for d in duplicates],
        "category_clusters": {k: len(v) for k, v in clusters.items()}
    }
