"""
Advanced Python AST Code Parser
Extracts structured CodeEntity metadata (classes, functions, methods, docstrings, signatures, decorators, call dependencies).
"""
import ast
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CodeEntity:
    """Represents a code-level entity extracted via AST static analysis."""
    id: str
    repository: str
    file_path: str
    entity_type: str  # "module", "class", "function", "test", "config"
    name: str
    qualified_name: str
    start_line: int
    end_line: int
    signature: str = ""
    docstring: str = ""
    parent: str = ""
    dependencies: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ASTCodeParser:
    """Parses Python source code using Python's built-in AST module."""

    def parse_file_content(self, repository: str, file_path: str, content: str) -> List[CodeEntity]:
        """Parse source code content and extract all CodeEntity declarations."""
        entities: List[CodeEntity] = []
        if not content or not content.strip():
            return entities

        # Add module-level entity
        lines = content.splitlines()
        clean_repo = repository.strip().replace("/", ":")
        module_id = f"{clean_repo}:{file_path}:module"
        
        try:
            tree = ast.parse(content, filename=file_path)
        except Exception as e:
            logger.warning(f"[ASTCodeParser] Syntax error in {file_path}: {e}")
            # Fallback module entity
            entities.append(CodeEntity(
                id=module_id,
                repository=repository,
                file_path=file_path,
                entity_type="module",
                name=file_path.split("/")[-1],
                qualified_name=file_path,
                start_line=1,
                end_line=len(lines)
            ))
            return entities

        # Collect top-level imports
        file_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    file_imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    file_imports.append(f"{mod}.{alias.name}" if mod else alias.name)

        docstring = ast.get_docstring(tree) or ""
        module_entity = CodeEntity(
            id=module_id,
            repository=repository,
            file_path=file_path,
            entity_type="module",
            name=file_path.split("/")[-1],
            qualified_name=file_path,
            start_line=1,
            end_line=len(lines),
            docstring=docstring,
            dependencies=file_imports
        )
        entities.append(module_entity)

        # Visitor to extract classes, functions, and methods
        class EntityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.scope_stack = []

            def visit_ClassDef(self, node: ast.ClassDef):
                qual_name = ".".join(self.scope_stack + [node.name])
                ent_id = f"{clean_repo}:{file_path}:class:{qual_name}"
                dec_names = [ast.unparse(d) for d in node.decorator_list if hasattr(ast, "unparse")]
                cls_doc = ast.get_docstring(node) or ""

                entities.append(CodeEntity(
                    id=ent_id,
                    repository=repository,
                    file_path=file_path,
                    entity_type="class",
                    name=node.name,
                    qualified_name=qual_name,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    signature=f"class {node.name}",
                    docstring=cls_doc,
                    parent=self.scope_stack[-1] if self.scope_stack else "",
                    decorators=dec_names
                ))

                self.scope_stack.append(node.name)
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef):
                self._handle_func(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self._handle_func(node)

            def _handle_func(self, node):
                qual_name = ".".join(self.scope_stack + [node.name])
                ent_type = "test" if node.name.startswith("test_") or file_path.startswith("tests/") else "function"
                ent_id = f"{clean_repo}:{file_path}:{ent_type}:{qual_name}"
                dec_names = [ast.unparse(d) for d in node.decorator_list if hasattr(ast, "unparse")]
                func_doc = ast.get_docstring(node) or ""

                # Signature representation
                args_str = ", ".join([a.arg for a in node.args.args])
                sig = f"def {node.name}({args_str})"

                # Collect function calls
                called_funcs = []
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        if isinstance(sub.func, ast.Name):
                            called_funcs.append(sub.func.id)
                        elif isinstance(sub.func, ast.Attribute):
                            called_funcs.append(sub.func.attr)

                entities.append(CodeEntity(
                    id=ent_id,
                    repository=repository,
                    file_path=file_path,
                    entity_type=ent_type,
                    name=node.name,
                    qualified_name=qual_name,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    signature=sig,
                    docstring=func_doc,
                    parent=self.scope_stack[-1] if self.scope_stack else "",
                    calls=list(set(called_funcs)),
                    decorators=dec_names
                ))

                self.scope_stack.append(node.name)
                self.generic_visit(node)
                self.scope_stack.pop()

        visitor = EntityVisitor()
        visitor.visit(tree)
        return entities
