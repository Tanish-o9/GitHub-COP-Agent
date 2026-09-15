"""
Engineering Memory 2.0
Categorized repository memory with confidence weighting, freshness decay, and strict Code > Memory precedence.
"""
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from repo_memory import RepoMemory

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Represents a single confidence-scored engineering memory entry."""
    category: str  # FACTS, ARCHITECTURE, CONVENTIONS, HISTORY, PREFERENCES, KNOWN_BUGS
    fact_text: str
    confidence: float = 1.0  # 0.0 to 1.0
    source: str = "automated_discovery"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EngineeringMemoryV2:
    """Advanced version-aware repository memory with precedence rules."""

    def __init__(self, repo_name: str, branch: str = "main"):
        self.repo_name = repo_name
        self.branch = branch
        self.base_memory = RepoMemory(repo_name, branch=branch)
        self.entries: List[MemoryEntry] = []
        self._initialize_default_memory()

    def _initialize_default_memory(self):
        """Seed memory from base RepoMemory snapshot."""
        base_ctx = self.base_memory.get_context_summary()
        self.entries.append(MemoryEntry(
            category="FACTS",
            fact_text=f"Repository {self.repo_name} uses default branch '{self.branch}'",
            confidence=1.0,
            source="github_mcp"
        ))

    def add_memory(self, category: str, fact_text: str, confidence: float = 0.9, source: str = "agent_discovery"):
        """Store a new memory entry with confidence score."""
        entry = MemoryEntry(
            category=category,
            fact_text=fact_text,
            confidence=min(1.0, max(0.0, confidence)),
            source=source,
            timestamp=time.time()
        )
        self.entries.append(entry)
        logger.info(f"[MemoryV2] Added memory entry under '{category}' for repo {self.repo_name}")

    def query_memory(self, category: Optional[str] = None, min_confidence: float = 0.5) -> List[MemoryEntry]:
        """Fetch memory entries filtered by category and confidence threshold."""
        results = []
        for e in self.entries:
            if min_confidence and e.confidence < min_confidence:
                continue
            if category and e.category != category:
                continue
            results.append(e)
        return results

    def resolve_code_conflict(self, fact_text: str, current_code_evidence: str) -> str:
        """
        Precedence Rule:
        Current Repository Code > Old Memory.
        If current repository evidence contradicts stored memory, current code wins.
        """
        if current_code_evidence:
            logger.info("[MemoryV2] Code Precedence Rule Triggered: Current repository code overrides stored memory.")
            return current_code_evidence
        return fact_text
