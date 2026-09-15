"""
Evaluation Report Generator Module
Exports structured evaluation and benchmark reports in JSON and Markdown formats.
"""
import os
import json
import time
from typing import Dict, Any, Optional


class ReportGenerator:
    """
    Generates and persists evaluation reports to reports/ directory.
    """

    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = reports_dir
        os.makedirs(self.reports_dir, exist_ok=True)

    def generate_report(self, metrics_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate JSON and Markdown report files.
        """
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        json_filename = f"eval_report_{timestamp_str}.json"
        md_filename = f"eval_report_{timestamp_str}.md"

        json_path = os.path.join(self.reports_dir, json_filename)
        md_path = os.path.join(self.reports_dir, md_filename)

        # Save JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metrics_data, f, indent=2)

        # Save Markdown
        md_lines = [
            "# 📊 AI Software Engineering Agent — Evaluation Report",
            "",
            f"**Timestamp**: `{metrics_data.get('timestamp')}`",
            f"**Total Benchmark Tests**: `{metrics_data.get('total_benchmark_tests')}`",
            f"**Overall Pass Rate**: `{metrics_data.get('overall_pass_rate_pct')}%`",
            "",
            "## Accuracy & Efficiency Metrics",
            f"- **Manager Routing Accuracy**: `{metrics_data.get('routing_accuracy_pct')}%`",
            f"- **RAG Top-3 Accuracy**: `{metrics_data.get('rag_top3_accuracy_pct')}%`",
            f"- **Concept Coverage**: `{metrics_data.get('concept_coverage_pct')}%`",
            f"- **Average Latency**: `{metrics_data.get('avg_latency_sec')}s`",
            "",
            "## Detailed Test Results",
            "| ID | Task Type | Expected Workflow | Actual Workflow | Routing Pass | Latency |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        for res in metrics_data.get("test_results", []):
            pass_str = "✅ PASS" if res["routing_passed"] else "❌ FAIL"
            md_lines.append(f"| `{res['id']}` | `{res['task_type']}` | `{res['expected_workflow']}` | `{res['actual_workflow']}` | {pass_str} | `{res['latency_sec']}s` |")

        md_content = "\n".join(md_lines)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return {
            "json_path": json_path,
            "md_path": md_path,
            "markdown_content": md_content
        }
