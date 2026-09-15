"""
Dependency Graph & Change Impact Analyzer
Traces imports, caller/callee graphs, and calculates impact reports for proposed code changes.
"""
import re
from typing import Dict, Any, List, Optional, Set


class DependencyAnalyzer:
    """
    Analyzes code relationships and calculates impact radius of proposed changes.
    """

    @staticmethod
    def extract_imports(file_content: str) -> List[str]:
        """Extract imported module names from Python file content."""
        imports = []
        for line in file_content.splitlines():
            line = line.strip()
            # import module
            m1 = re.match(r'^import\s+([A-Za-z0-9_\.]+)', line)
            if m1:
                imports.append(m1.group(1))
            # from module import symbol
            m2 = re.match(r'^from\s+([A-Za-z0-9_\.]+)\s+import', line)
            if m2:
                imports.append(m2.group(1))
        return imports

    @staticmethod
    def analyze_change_impact(
        target_file: str,
        repo_files: List[Dict[str, Any]],
        modified_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate direct dependencies, caller files, related tests, and regression risks.
        """
        target_base = target_file.replace(".py", "").replace("/", ".").replace("\\", ".")
        module_name = target_file.split("/")[-1].replace(".py", "")

        direct_dependencies: Set[str] = set()
        affected_files: Set[str] = set()
        related_tests: Set[str] = set()

        # If modified content is provided, extract its direct imports
        if modified_content:
            imports = DependencyAnalyzer.extract_imports(modified_content)
            for imp in imports:
                direct_dependencies.add(imp)

        # Scan repo files to find who imports target module
        for f in repo_files:
            path = f.get("path", "")
            content = f.get("content", "")

            if path == target_file:
                continue

            # Check if this file imports target module
            if module_name and (f"import {module_name}" in content or f"from {module_name}" in content or module_name in content):
                if "test" in path.lower():
                    related_tests.add(path)
                else:
                    affected_files.add(path)

        regression_risks = [
            f"Functions in {len(affected_files)} dependent module(s) rely on exported signatures in `{target_file}`.",
            f"Existing unit tests in {len(related_tests)} test file(s) must be executed to prevent regressions."
        ]

        impact_report = {
            "target_file": target_file,
            "direct_dependencies": list(direct_dependencies),
            "affected_files": list(affected_files),
            "related_tests": list(related_tests),
            "regression_risks": regression_risks
        }

        return impact_report

    @staticmethod
    def format_impact_markdown(report: Dict[str, Any]) -> str:
        """Format impact report into standardized Markdown structure."""
        changed = f"- [`{report['target_file']}`](file:///{report['target_file']})"
        deps = "\n".join([f"- `{d}`" for d in report["direct_dependencies"]]) if report["direct_dependencies"] else "No external module dependencies."
        aff = "\n".join([f"- [`{f}`](file:///{f})" for f in report["affected_files"]]) if report["affected_files"] else "No downstream dependent files detected."
        tests = "\n".join([f"- [`{t}`](file:///{t})" for t in report["related_tests"]]) if report["related_tests"] else "No existing test files directly reference this module."
        risks = "\n".join([f"- {r}" for r in report["regression_risks"]])

        return f"""# ⚡ Change Impact Analysis Report

## Changed Files
{changed}

## Direct Dependencies
{deps}

## Potentially Affected Files
{aff}

## Related Tests
{tests}

## Regression Risks
{risks}
"""
