"""
Duplicate Issue Detection & Issue Clustering Engine
Uses TF-IDF term overlap and symbol matching to identify duplicate issues and cluster issues into functional categories.
"""
import re
import math
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class DuplicateCandidate:
    """Represents a candidate duplicate issue."""
    issue_number: int
    duplicate_issue_number: int
    similarity_score: float
    matched_terms: List[str] = field(default_factory=list)
    recommendation: str = "FLAG_FOR_REVIEW"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class IssueSimilarityEngine:
    """Detects duplicate issues and groups repository issues into category clusters."""

    def calculate_similarity(self, issue_a: Dict[str, Any], issue_b: Dict[str, Any]) -> float:
        text_a = (issue_a.get("title", "") + " " + issue_a.get("body", "")).lower()
        text_b = (issue_b.get("title", "") + " " + issue_b.get("body", "")).lower()

        terms_a = set(re.findall(r'\w+', text_a))
        terms_b = set(re.findall(r'\w+', text_b))

        if not terms_a or not terms_b:
            return 0.0

        intersection = terms_a.intersection(terms_b)
        union = terms_a.union(terms_b)

        # Jaccard similarity score
        jaccard = len(intersection) / len(union) if union else 0.0

        # Title exact word match bonus
        title_a = set(re.findall(r'\w+', issue_a.get("title", "").lower()))
        title_b = set(re.findall(r'\w+', issue_b.get("title", "").lower()))
        title_overlap = len(title_a.intersection(title_b)) / max(len(title_a), 1) if title_a else 0.0

        score = round((jaccard * 0.6 + title_overlap * 0.4) * 100, 1)
        return min(100.0, score)

    def find_duplicates(self, target_issue: Dict[str, Any], existing_issues: List[Dict[str, Any]], threshold: float = 60.0) -> List[DuplicateCandidate]:
        candidates = []
        target_num = target_issue.get("number", 0)

        for issue in existing_issues:
            other_num = issue.get("number", 0)
            if other_num == target_num:
                continue

            sim_score = self.calculate_similarity(target_issue, issue)
            if sim_score >= threshold:
                terms_a = set(re.findall(r'\w+', target_issue.get("title", "").lower()))
                terms_b = set(re.findall(r'\w+', issue.get("title", "").lower()))
                matched = list(terms_a.intersection(terms_b))

                candidates.append(DuplicateCandidate(
                    issue_number=target_num,
                    duplicate_issue_number=other_num,
                    similarity_score=sim_score,
                    matched_terms=matched,
                    recommendation=f"Issue #{target_num} appears similar to Issue #{other_num} ({sim_score}% match)"
                ))

        candidates.sort(key=lambda x: x.similarity_score, reverse=True)
        return candidates

    def cluster_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        clusters: Dict[str, List[Dict[str, Any]]] = {
            "authentication": [],
            "api": [],
            "database": [],
            "performance": [],
            "security": [],
            "general": []
        }

        for issue in issues:
            text = (issue.get("title", "") + " " + issue.get("body", "")).lower()
            if any(k in text for k in ["auth", "login", "jwt", "password", "token"]):
                clusters["authentication"].append(issue)
            elif any(k in text for k in ["api", "route", "endpoint", "fastapi", "http"]):
                clusters["api"].append(issue)
            elif any(k in text for k in ["db", "database", "sql", "postgres", "table", "model"]):
                clusters["database"].append(issue)
            elif any(k in text for k in ["slow", "latency", "performance", "memory", "timeout"]):
                clusters["performance"].append(issue)
            elif any(k in text for k in ["security", "cve", "injection", "vulnerability"]):
                clusters["security"].append(issue)
            else:
                clusters["general"].append(issue)

        return clusters
