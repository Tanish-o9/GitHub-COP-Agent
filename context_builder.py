"""
Smart Context Builder
Synthesizes user requests, memory, RAG semantic chunks, dependency graphs, and live MCP code context into focused prompts.
"""
from typing import Dict, Any, List, Optional
from repo_memory import RepoMemory
from rag_engine import CodeChunk
from agent_tracer import AgentTracer


class SmartContextBuilder:
    """
    Synthesizes focused multi-source context prompts without sending entire repos.
    """

    @staticmethod
    def build_focused_context(
        user_request: str,
        repo_name: str,
        memory: RepoMemory,
        rag_chunks: Optional[List[Dict[str, Any]]] = None,
        relevant_files: Optional[List[Dict[str, Any]]] = None,
        dependency_info: Optional[Dict[str, Any]] = None,
        issue_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build focused context dictionary and formatted context markdown string.
        """
        context_parts = []

        # 1. Add Categorized Durable Memory
        mem_summary = memory.get_context_summary()
        if mem_summary and mem_summary != "No prior repository memory saved.":
            context_parts.append(f"### 📦 Categorized Repository Memory\n{mem_summary}\n")

        # 2. Add Issue Context
        if issue_data:
            context_parts.append(f"### 🐛 Target Issue Context\n- **Issue #{issue_data.get('number')}**: {issue_data.get('title')}\n- **Description**: {issue_data.get('body', '')[:300]}\n")

        # 3. Add RAG Semantic Chunks & Citations
        if rag_chunks:
            context_parts.append("### 🔍 Relevant Code Snippets (RAG Retrieval)")
            for item in rag_chunks[:3]:
                chunk: CodeChunk = item["chunk"]
                context_parts.append(f"**Source**: {item['citation']} (Symbol: `{chunk.symbol_name}`)\n```python\n{chunk.content[:400]}\n```\n")

        # 4. Add Relevant File Context
        if relevant_files:
            context_parts.append("### 📄 Active File Contents")
            for f in relevant_files[:2]:
                path = f.get("path", "")
                content = f.get("content", "")
                snippet = "\n".join(content.splitlines()[:30])
                context_parts.append(f"**File**: [`{path}`](file:///{path})\n```python\n{snippet}\n```\n")

        # 5. Add Dependency Analysis
        if dependency_info:
            affected = dependency_info.get("affected_files", [])
            context_parts.append(f"### 🔗 Dependency Graph\n- **Affected Files**: {', '.join(affected) if affected else 'None'}\n")

        combined_text = "\n".join(context_parts)
        sanitized_text = AgentTracer.sanitize_secrets(combined_text)

        return {
            "raw_text": sanitized_text,
            "has_memory": bool(mem_summary),
            "rag_chunk_count": len(rag_chunks) if rag_chunks else 0,
            "relevant_file_count": len(relevant_files) if relevant_files else 0
        }
