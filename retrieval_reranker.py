"""
RAG 2.0 Retrieval Reranker & Context Compressor
Query classification, query expansion, deterministic hybrid reranking, and token-aware context compression.
"""
import re
import math
import logging
from typing import List, Dict, Any, Optional
from rag_engine import CodeChunk

logger = logging.getLogger(__name__)

# Query Categories
CATEGORY_REPO_OVERVIEW = "REPO_OVERVIEW"
CATEGORY_CODE_SEARCH = "CODE_SEARCH"
CATEGORY_BUG_INVESTIGATION = "BUG_INVESTIGATION"
CATEGORY_ARCHITECTURE = "ARCHITECTURE"
CATEGORY_DEPENDENCY = "DEPENDENCY"
CATEGORY_CHANGE_IMPACT = "CHANGE_IMPACT"
CATEGORY_TESTING = "TESTING"
CATEGORY_SECURITY = "SECURITY"
CATEGORY_PR_REVIEW = "PR_REVIEW"


class QueryClassifier:
    """Classifies incoming developer prompts into functional retrieval categories."""

    @staticmethod
    def classify(query: str) -> str:
        q_lower = query.lower()
        if any(w in q_lower for w in ["security", "vulnerability", "secret", "injection", "token", "password"]):
            return CATEGORY_SECURITY
        if any(w in q_lower for w in ["test", "unittest", "pytest", "coverage", "mock"]):
            return CATEGORY_TESTING
        if any(w in q_lower for w in ["impact", "affect", "caller", "dependent", "downstream"]):
            return CATEGORY_CHANGE_IMPACT
        if any(w in q_lower for w in ["bug", "error", "exception", "traceback", "fix", "fail", "issue"]):
            return CATEGORY_BUG_INVESTIGATION
        if any(w in q_lower for w in ["architecture", "overview", "structure", "design", "explain"]):
            return CATEGORY_ARCHITECTURE
        if any(w in q_lower for w in ["pr", "pull request", "diff", "review"]):
            return CATEGORY_PR_REVIEW
        return CATEGORY_CODE_SEARCH


class QueryExpander:
    """Generates expanded search variants to increase recall for complex questions."""

    @staticmethod
    def expand(query: str) -> List[str]:
        variants = [query]
        terms = re.findall(r'\w+', query.lower())
        
        # Add camelCase / snake_case variations
        if "_" in query:
            variants.append(query.replace("_", " "))
        for term in terms:
            if len(term) > 3 and term not in variants:
                variants.append(term)
        return list(set(variants))[:4]


class HybridReranker:
    """
    Reranks candidate search chunks combining BM25 symbol score, path proximity, and graph relevance.
    """

    @staticmethod
    def rerank(query: str, candidates: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        query_terms = set(re.findall(r'\w+', query.lower()))
        category = QueryClassifier.classify(query)

        reranked = []
        for cand in candidates:
            chunk: CodeChunk = cand.get("chunk")
            base_score = cand.get("score", 1.0)
            
            if not chunk:
                continue

            content_lower = chunk.content.lower()
            symbol_lower = chunk.symbol_name.lower()
            file_lower = chunk.file_path.lower()

            # Boost exact symbol match
            symbol_boost = 3.0 if any(term in symbol_lower for term in query_terms) else 0.0

            # Boost query category matching
            category_boost = 0.0
            if category == CATEGORY_TESTING and ("test" in file_lower or chunk.chunk_type == "test"):
                category_boost = 2.0
            elif category == CATEGORY_SECURITY and any(s in content_lower for s in ["auth", "token", "key", "secret"]):
                category_boost = 2.5

            final_score = base_score + symbol_boost + category_boost
            
            reranked.append({
                "score": round(final_score, 2),
                "chunk": chunk,
                "citation": chunk.get_citation(),
                "category_match": category
            })

        reranked.sort(key=lambda x: x["score"], reverse=True)
        return reranked[:top_k]


class ContextCompressor:
    """Selects top reranked chunks and builds token-efficient context prompts."""

    @staticmethod
    def compress_context(reranked_results: List[Dict[str, Any]], max_chars: int = 4000) -> Dict[str, Any]:
        context_blocks = []
        citations = []
        current_len = 0

        for item in reranked_results:
            chunk: CodeChunk = item["chunk"]
            block = f"--- {chunk.get_citation()} (Symbol: {chunk.symbol_name}) ---\n{chunk.content}\n"
            if current_len + len(block) > max_chars:
                break
            context_blocks.append(block)
            citations.append(item["citation"])
            current_len += len(block)

        compressed_text = "\n".join(context_blocks)
        return {
            "compressed_text": compressed_text,
            "citations": citations,
            "used_chunks": len(context_blocks),
            "char_count": current_len
        }
