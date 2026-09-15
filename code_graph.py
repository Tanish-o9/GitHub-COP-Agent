"""
Repository Code Intelligence Graph
Maintains code symbol nodes and relationship edges (imports, calls, depends_on, tested_by) with incremental update support.
"""
import logging
from typing import Dict, Any, List, Set, Optional
from code_parser import CodeEntity, ASTCodeParser
from github_mcp import GitHubMCPTools

logger = logging.getLogger(__name__)


class CodeIntelligenceGraph:
    """In-memory and relational code graph representation of repository symbols and call linkages."""

    def __init__(self, repository: str):
        self.repository = repository
        self.entities: Dict[str, CodeEntity] = {}  # id -> CodeEntity
        self.edges: Dict[str, Set[str]] = {}       # source_id -> set(target_ids)
        self.reverse_edges: Dict[str, Set[str]] = {}# target_id -> set(source_ids)
        self.file_to_entities: Dict[str, List[str]] = {} # file_path -> list(entity_ids)

    def add_entity(self, entity: CodeEntity):
        """Add or replace a code entity in the graph."""
        self.entities[entity.id] = entity
        self.file_to_entities.setdefault(entity.file_path, []).append(entity.id)
        if entity.id not in self.edges:
            self.edges[entity.id] = set()
        if entity.id not in self.reverse_edges:
            self.reverse_edges[entity.id] = set()

    def add_relationship(self, source_id: str, target_id: str, rel_type: str = "depends_on"):
        """Add a directed relationship edge between two entities."""
        if source_id in self.entities and target_id in self.entities:
            self.edges.setdefault(source_id, set()).add(target_id)
            self.reverse_edges.setdefault(target_id, set()).add(source_id)

    def build_from_files(self, file_map: Dict[str, str]):
        """Build graph from a map of file_path -> file_content."""
        parser = ASTCodeParser()
        self.entities.clear()
        self.edges.clear()
        self.reverse_edges.clear()
        self.file_to_entities.clear()

        # Step 1: Parse entities
        for file_path, content in file_map.items():
            parsed_entities = parser.parse_file_content(self.repository, file_path, content)
            for ent in parsed_entities:
                self.add_entity(ent)

        # Step 2: Infer relationships (imports, calls, test linkages)
        symbol_map = {e.name: e.id for e in self.entities.values()}

        for ent_id, ent in self.entities.items():
            # Link calls to target entities
            for call_name in ent.calls:
                if call_name in symbol_map and symbol_map[call_name] != ent_id:
                    self.add_relationship(ent_id, symbol_map[call_name], rel_type="calls")

            # Link tests to target code entities
            if ent.entity_type == "test":
                for other_name, other_id in symbol_map.items():
                    if other_name in ent.name and other_id != ent_id:
                        self.add_relationship(ent_id, other_id, rel_type="tested_by")

    def update_file_incremental(self, file_path: str, content: str):
        """Incrementally update graph nodes and edges for a modified file."""
        # Purge existing entities for file
        old_entity_ids = self.file_to_entities.get(file_path, [])
        for eid in old_entity_ids:
            self.entities.pop(eid, None)
            self.edges.pop(eid, None)
            self.reverse_edges.pop(eid, None)

        self.file_to_entities[file_path] = []

        # Parse new content
        parser = ASTCodeParser()
        new_entities = parser.parse_file_content(self.repository, file_path, content)
        for ent in new_entities:
            self.add_entity(ent)

    def get_dependencies(self, entity_id: str) -> List[CodeEntity]:
        """Fetch entities that target entity depends on."""
        target_ids = self.edges.get(entity_id, set())
        return [self.entities[tid] for tid in target_ids if tid in self.entities]

    def get_dependents(self, entity_id: str) -> List[CodeEntity]:
        """Fetch entities that depend on target entity."""
        source_ids = self.reverse_edges.get(entity_id, set())
        return [self.entities[sid] for sid in source_ids if sid in self.entities]

    def get_callers(self, symbol_name: str) -> List[CodeEntity]:
        """Fetch entities that call symbol_name."""
        callers = []
        for ent in self.entities.values():
            if symbol_name in ent.calls:
                callers.append(ent)
        return callers

    def get_related_tests(self, file_path: str) -> List[CodeEntity]:
        """Fetch test entities linked to code in file_path."""
        entity_ids = self.file_to_entities.get(file_path, [])
        related_tests = set()

        for eid in entity_ids:
            dependents = self.get_dependents(eid)
            for dep in dependents:
                if dep.entity_type == "test":
                    related_tests.add(dep)

        return list(related_tests)

    def get_affected_nodes(self, file_path: str) -> Dict[str, Any]:
        """Compute full impact radius for a modified file."""
        entity_ids = self.file_to_entities.get(file_path, [])
        direct_dependents = set()
        test_suites = set()

        for eid in entity_ids:
            deps = self.get_dependents(eid)
            for d in deps:
                if d.entity_type == "test":
                    test_suites.add(d.file_path)
                else:
                    direct_dependents.add(d.file_path)

        return {
            "target_file": file_path,
            "entities_count": len(entity_ids),
            "direct_dependent_files": list(direct_dependents),
            "affected_test_suites": list(test_suites),
            "impact_level": "HIGH" if len(direct_dependents) > 3 else "MEDIUM"
        }

    def get_summary(self) -> Dict[str, Any]:
        """Fetch structural summary of the code graph."""
        return {
            "repository": self.repository,
            "total_entities": len(self.entities),
            "total_edges": sum(len(e) for e in self.edges.values()),
            "total_files": len(self.file_to_entities)
        }
