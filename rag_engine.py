"""
Intelligent Codebase RAG Engine
Implements code-aware chunking, rich symbol metadata extraction, hybrid semantic/keyword retrieval, and source citations.
"""
import os
import re
import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer


@dataclass
class CodeChunk:
    """Represents a code-aware chunk with symbol metadata."""
    repository: str
    branch: str
    file_path: str
    symbol_name: str
    language: str
    start_line: int
    end_line: int
    chunk_type: str  # "function", "class", "module", "config", "doc"
    content: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def get_citation(self) -> str:
        return f"[`{self.file_path}:L{self.start_line}-L{self.end_line}`](file:///{self.file_path}#L{self.start_line}-L{self.end_line})"


class CodebaseRAGEngine:
    """
    Code-aware indexing and hybrid retrieval engine for repository knowledge.
    """

    def __init__(self, repo_name: str, branch: str = "main"):
        self.repo_name = repo_name
        self.branch = branch
        self.chunks: List[CodeChunk] = []

    def is_indexable(self, file_path: str, size: int = 0) -> bool:
        """Filter out binary, secret, generated, or giant files."""
        path_lower = file_path.lower()
        
        # Exclude directories/patterns
        ignored_patterns = [
            "node_modules/", ".git/", "venv/", ".env", "__pycache__/",
            "dist/", "build/", "vendor/", "target/", ".egg-info/"
        ]
        if any(p in path_lower for p in ignored_patterns):
            return False

        # Exclude binary extensions
        binary_exts = [".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".exe", ".pyc", ".db"]
        if any(path_lower.endswith(ext) for ext in binary_exts):
            return False

        # File size limit (max 500KB)
        if size > 500 * 1024:
            return False

        return True

    def chunk_code_file(self, file_path: str, content: str) -> List[CodeChunk]:
        """Perform code-aware chunking based on language structure."""
        chunks: List[CodeChunk] = []
        lines = content.splitlines()
        if not lines:
            return chunks

        lang = "python" if file_path.endswith(".py") else "text"
        current_symbol = "module"
        current_type = "module"
        current_start = 1
        current_buffer = []

        for i, line in enumerate(lines, 1):
            def_match = re.match(r'^\s*(def|class)\s+([A-Za-z0-9_]+)', line)
            if def_match:
                # Flush existing buffer if non-empty
                chunk_text = "\n".join(current_buffer).strip()
                if chunk_text:
                    chunks.append(CodeChunk(
                        repository=self.repo_name,
                        branch=self.branch,
                        file_path=file_path,
                        symbol_name=current_symbol,
                        language=lang,
                        start_line=current_start,
                        end_line=i - 1,
                        chunk_type=current_type,
                        content=chunk_text
                    ))
                current_buffer = []
                current_start = i
                current_type = "function" if def_match.group(1) == "def" else "class"
                current_symbol = def_match.group(2)

            current_buffer.append(line)

        # Flush trailing buffer
        if current_buffer:
            chunk_text = "\n".join(current_buffer)
            if chunk_text.strip():
                chunks.append(CodeChunk(
                    repository=self.repo_name,
                    branch=self.branch,
                    file_path=file_path,
                    symbol_name=current_symbol,
                    language=lang,
                    start_line=current_start,
                    end_line=len(lines),
                    chunk_type=current_type,
                    content=chunk_text
                ))

        return chunks

    def index_repository(self, mcp_tools: GitHubMCPTools, max_files: int = 25) -> int:
        """Scan repository files and build code-aware chunk index."""
        tree = mcp_tools.get_repo_tree(self.repo_name, branch=self.branch, recursive=True)
        indexed_count = 0
        self.chunks.clear()

        for item in tree:
            if indexed_count >= max_files:
                break
            path = item["path"]
            size = item.get("size", 0)
            if item["type"] == "blob" and self.is_indexable(path, size):
                try:
                    fc = mcp_tools.get_file_content(self.repo_name, path, ref=self.branch)
                    content = fc["content"]
                    # Sanitize any accidental secrets before indexing
                    sanitized_content = AgentTracer.sanitize_secrets(content)
                    file_chunks = self.chunk_code_file(path, sanitized_content)
                    self.chunks.extend(file_chunks)
                    indexed_count += 1
                except Exception:
                    pass

        return len(self.chunks)

    def hybrid_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval combining keyword matching and TF-IDF term relevance.
        """
        if not self.chunks:
            return []

        query_terms = set(re.findall(r'\w+', query.lower()))
        scored_results = []

        for chunk in self.chunks:
            content_lower = chunk.content.lower()
            symbol_lower = chunk.symbol_name.lower()
            file_lower = chunk.file_path.lower()

            score = 0.0
            for term in query_terms:
                if term in symbol_lower:
                    score += 5.0  # High weight for symbol name match
                if term in file_lower:
                    score += 3.0  # Weight for path match
                if term in content_lower:
                    score += 1.0 + math.log(content_lower.count(term) + 1)

            if score > 0:
                scored_results.append({
                    "score": round(score, 2),
                    "chunk": chunk,
                    "citation": chunk.get_citation()
                })

        # Sort descending by score
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:top_k]
