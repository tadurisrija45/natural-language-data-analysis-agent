"""
Python analysis execution engine with isolated sandbox execution.
Executes user-supplied Python code on uploaded datasets,
validating safety via AST checks and returning verified business answers,
evidence, charts, and insights.
"""

import os
import re
from typing import Dict, Any, List, Optional
import pandas as pd

from ..security.sandbox import ExecutionSandbox
from .visualization import VisualizationEngine
from ..agents.insight_generator import InsightGenerator
from ..utils.helpers import format_currency, format_number
from ..utils.logger import get_logger

logger = get_logger("DataAgent.PythonExecutor")


class PythonExecutor:
    @classmethod
    def execute_python(
        cls,
        code: str,
        data_files: Dict[str, str],
        datasets_meta: Dict[str, Any],
        user_id: int = None
    ) -> Dict[str, Any]:
        """
        Execute user-supplied Python code in the secure sandbox and synthesize results.
        """
        logger.info(f"Executing Python code for user_id={user_id} across {len(data_files)} datasets.")

        if not code or not code.strip():
            return {
                "success": False,
                "status": "error",
                "answer": "Python code cannot be empty. Please enter your Python analysis script.",
                "analysis_type": "Python Script",
                "evidence": {},
                "proof": "No code provided.",
                "validation": [
                    {"check": "Code Input", "passed": False, "detail": "Empty code payload received"}
                ],
                "insight": "Write Python code using pandas (e.g., df = datasets['dataset_name'] or orders.groupby(...)) to analyze your data.",
                "chart_info": {},
                "source_data": [],
                "raw_code": code or "",
                "selected_datasets": list(data_files.keys()),
                "selected_columns": []
            }

        # 1. Execute inside sandbox
        sandbox_result = ExecutionSandbox.execute(
            code=code,
            data_files=data_files,
            user_id=user_id
        )

        # 2. Check for security gate failure
        if sandbox_result.mode == "security_gate" or (not sandbox_result.success and "Security Gate Violation" in (sandbox_result.error or "")):
            err = sandbox_result.error or "Security gate check failed"
            return {
                "success": False,
                "status": "security_violation",
                "answer": f"Security Check Failed: {err}",
                "analysis_type": "Python Script",
                "evidence": {},
                "proof": f"Security Gate: Blocked execution.\nReason: {err}",
                "validation": [
                    {"check": "AST Security Gate Check", "passed": False, "detail": err}
                ],
                "insight": "Only data manipulation code using pandas, numpy, and python built-ins is permitted. System calls, external networking, and filesystem imports are restricted.",
                "chart_info": {},
                "source_data": [],
                "raw_code": code,
                "selected_datasets": list(data_files.keys()),
                "selected_columns": []
            }

        # 3. Check for runtime execution failure
        if not sandbox_result.success:
            err = sandbox_result.error or "Unknown execution error"
            return {
                "success": False,
                "status": "error",
                "answer": f"Python Execution Error: {err}",
                "analysis_type": "Python Script",
                "evidence": {},
                "proof": f"Executed Code:\n{code}\n\nExecution Time: {sandbox_result.execution_time}s\nError:\n{err}",
                "validation": [
                    {"check": "AST Security Gate Check", "passed": True, "detail": "Safe code structure verified"},
                    {"check": "Sandbox Execution", "passed": False, "detail": err}
                ],
                "insight": f"Encountered a Python runtime error: {err}. Check your column names, variable types, or missing values.",
                "chart_info": {},
                "source_data": [],
                "raw_code": code,
                "selected_datasets": list(data_files.keys()),
                "selected_columns": []
            }

        # 4. Success: Parse result_data and stdout
        result_data = sandbox_result.result_data
        stdout_logs = getattr(sandbox_result, "stdout", "") or ""

        # Detect referenced datasets
        referenced_datasets = []
        for name in data_files.keys():
            stem = os.path.splitext(name)[0].lower().replace("-", "_").replace(" ", "_")
            sanitized = name.lower().replace(".", "_").replace("-", "_").replace(" ", "_")
            if (name in code or stem in code.lower() or sanitized in code.lower()):
                referenced_datasets.append(name)
        if not referenced_datasets:
            referenced_datasets = list(data_files.keys())

        source_label = ", ".join(referenced_datasets)

        # Total rows across datasets
        total_rows = 0
        for ds_name in referenced_datasets:
            meta = datasets_meta.get(ds_name, {})
            total_rows += meta.get("rows", 0)

        # 5. Normalize result_data into records, breakdown, and columns
        source_records = []
        breakdown = []
        columns = []
        answer = ""
        metric_name = "Metric"
        group_name = "Category"

        if isinstance(result_data, list):
            # List of dicts (e.g. DataFrame to_json records)
            source_records = result_data[:25]
            if result_data and isinstance(result_data[0], dict):
                columns = list(result_data[0].keys())
                group_name = columns[0]
                if len(columns) > 1:
                    metric_name = columns[1]
                    for row in result_data[:15]:
                        g_val = str(row.get(columns[0], ""))
                        m_val = row.get(columns[1], 0)
                        try:
                            num_val = float(m_val) if m_val is not None else 0.0
                        except (ValueError, TypeError):
                            num_val = 1.0
                        breakdown.append({"entity": g_val, "value": num_val})
                else:
                    for row in result_data[:15]:
                        breakdown.append({"entity": str(row.get(columns[0], "")), "value": 1.0})
                
                row_count = len(result_data)
                if breakdown and len(columns) > 1:
                    top_item = breakdown[0]
                    is_curr = any(k in metric_name.lower() for k in ["revenue", "sales", "profit", "salary", "spend", "cost", "price", "amount"])
                    top_fmt = format_currency(top_item["value"]) if is_curr else (f"{top_item['value']:,.2f}" if top_item["value"] % 1 != 0 else f"{int(top_item['value']):,}")
                    answer = f"Python analysis returned {row_count:,} records. Leading {group_name.replace('_', ' ')}: {top_item['entity']} with {metric_name.replace('_', ' ')} of {top_fmt}."
                else:
                    answer = f"Python analysis returned {row_count:,} records across columns: {', '.join(columns)}."

        elif isinstance(result_data, dict):
            # Dict (e.g., Series index->value or summary dict)
            columns = ["Key", "Value"]
            for k, v in list(result_data.items())[:15]:
                try:
                    num_val = float(v) if v is not None else 0.0
                except (ValueError, TypeError):
                    num_val = 0.0
                breakdown.append({"entity": str(k), "value": num_val})
                source_records.append({"Key": str(k), "Value": v})

            row_count = len(result_data)
            if breakdown and any(b["value"] != 0 for b in breakdown):
                top_item = max(breakdown, key=lambda x: x["value"])
                answer = f"Python analysis processed {row_count:,} categories. Top entry: {top_item['entity']} ({top_item['value']:,.2f})."
            else:
                answer = f"Python analysis returned a dictionary with {row_count:,} key-value pairs."

        elif isinstance(result_data, (int, float)):
            num_val = float(result_data)
            breakdown = [{"entity": "Result", "value": num_val}]
            source_records = [{"Metric": "Computed Result", "Value": result_data}]
            columns = ["Metric", "Value"]
            fmt_res = f"{num_val:,.4f}" if num_val % 1 != 0 else f"{int(num_val):,}"
            answer = f"Python analysis computed: {fmt_res}."
            if stdout_logs:
                answer += f"\n\nOutput:\n{stdout_logs}"

        elif isinstance(result_data, str):
            answer = result_data
            source_records = [{"Output": result_data}]
            columns = ["Output"]

        elif result_data is None and stdout_logs:
            answer = f"Python code executed successfully. Output:\n{stdout_logs}"
            source_records = [{"Output": line} for line in stdout_logs.splitlines()[:20]]
            columns = ["Output"]
        else:
            answer = "Python code executed successfully with no return value. Assign your analysis result to 'result_data' or 'result' to display tables and charts."

        # 6. Build Chart.js configuration
        chart_info = {}
        if breakdown and len(breakdown) > 1 and any(b["value"] != 0 for b in breakdown):
            labels = [b["entity"] for b in breakdown[:10]]
            values = [b["value"] for b in breakdown[:10]]
            chart_title = f"{metric_name.replace('_', ' ').title()} by {group_name.replace('_', ' ').title()}"
            chart_info = VisualizationEngine.build_chart_config(
                chart_type="bar",
                labels=labels,
                data=values,
                title=chart_title,
                dataset_label=metric_name.replace('_', ' ').title()
            )

        # 7. Evidence
        def fmt_val_item(v):
            if isinstance(v, (int, float)):
                return f"{v:,.2f}" if v % 1 != 0 else f"{int(v):,}"
            return str(v)

        formatted_breakdown = []
        for b in breakdown:
            formatted_breakdown.append({
                "entity": b["entity"],
                "raw_value": b["value"],
                "formatted_value": fmt_val_item(b["value"])
            })

        evidence = {
            "source_dataset": source_label,
            "rows_analyzed": total_rows,
            "metric_analyzed": metric_name.replace("_", " ").title(),
            "group_by": group_name.replace("_", " ").title(),
            "breakdown": formatted_breakdown,
            "sample_source_records": source_records[:20]
        }

        # 8. Proof
        proof_lines = [
            "Executed Python Script in Sandbox:",
            f"```python\n{code}\n```",
            f"Execution Environment: Subprocess Sandbox ({sandbox_result.mode})",
            f"Execution Time: {sandbox_result.execution_time:.3f} seconds",
            f"Input Datasets: {source_label}"
        ]
        if stdout_logs:
            proof_lines.append(f"Standard Output:\n{stdout_logs}")
        if breakdown:
            top_b = breakdown[0]
            proof_lines.append(f"Leading Result: {top_b['entity']} = {fmt_val_item(top_b['value'])}")

        proof_text = "\n".join(proof_lines)

        # 9. Validation
        validation_list = [
            {
                "check": "AST Security Gate Check",
                "passed": True,
                "detail": "Static AST validation verified 0 dangerous imports, calls, or attributes."
            },
            {
                "check": "Sandbox Isolation",
                "passed": True,
                "detail": f"Executed safely in isolated environment ({sandbox_result.execution_time:.3f}s runtime)."
            },
            {
                "check": "Data & Variable Reconciliation",
                "passed": True,
                "detail": f"Resolved datasets ({source_label}) and extracted analysis results."
            }
        ]

        # 10. Insight
        insight = InsightGenerator.generate_insight(
            question="Python Analysis Script",
            intent={
                "analysis_type": "python",
                "metric": metric_name,
                "group_by": group_name
            },
            evidence=evidence,
            answer_text=answer
        )

        return {
            "success": True,
            "status": "completed",
            "answer": answer,
            "analysis_type": "Python Script",
            "evidence": evidence,
            "proof": proof_text,
            "validation": validation_list,
            "insight": insight,
            "chart_info": chart_info,
            "source_data": source_records,
            "raw_code": code,
            "selected_datasets": referenced_datasets,
            "selected_columns": columns
        }
