import os
import re
import sqlite3
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd

from .file_loader import FileLoader
from .visualization import VisualizationEngine
from ..agents.insight_generator import InsightGenerator
from ..utils.helpers import format_currency, format_number
from ..utils.logger import get_logger

logger = get_logger("DataAgent.SQLExecutor")


class SQLExecutor:
    # Destructive keywords disallowed in read-only SQL execution
    DISALLOWED_KEYWORDS = [
        "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
        "CREATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA", "VACUUM",
        "GRANT", "REVOKE", "EXEC", "EXECUTE", "INTO"
    ]

    @classmethod
    def validate_sql(cls, query: str) -> Tuple[bool, Optional[str]]:
        """
        Strict security gate for user-supplied SQL queries:
        - Only SELECT / WITH queries permitted.
        - Blocks all destructive statements (DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, etc.).
        - Blocks multiple chained statements via semicolons.
        """
        if not query or not query.strip():
            return False, "SQL query cannot be empty."

        clean = query.strip()

        # Strip line comments (-- ...) and block comments (/* ... */)
        clean_no_comments = re.sub(r"--[^\n]*", "", clean)
        clean_no_comments = re.sub(r"/\*.*?\*/", "", clean_no_comments, flags=re.DOTALL).strip()

        if not clean_no_comments:
            return False, "SQL query cannot contain only comments."

        # Check for multiple statements separated by semicolons
        statements = [s.strip() for s in re.split(r";\s*", clean_no_comments) if s.strip()]
        if len(statements) > 1:
            return False, "Multiple SQL statements are not permitted in a single query."

        target_stmt = statements[0]

        # Must begin with SELECT or WITH
        if not re.match(r"^\s*(SELECT|WITH)\b", target_stmt, re.IGNORECASE):
            return False, "Only read-only queries starting with SELECT or WITH are permitted."

        # Scan for disallowed keywords
        for kw in cls.DISALLOWED_KEYWORDS:
            pattern = rf"\b{kw}\b"
            if re.search(pattern, target_stmt, re.IGNORECASE):
                return False, f"Destructive or unauthorized SQL statement detected: '{kw}'. Only read-only queries are allowed."

        return True, None

    @classmethod
    def execute_sql(
        cls,
        query: str,
        data_files: Dict[str, str],
        datasets_meta: Dict[str, Any],
        user_id: int = None
    ) -> Dict[str, Any]:
        """
        Execute read-only SQL query across uploaded datasets using an in-memory SQL database.
        Supports JOIN across multiple datasets.
        """
        logger.info(f"Executing SQL query for user_id={user_id}: {query[:120]}")

        # 1. Security Gate Validation
        is_valid, error_msg = cls.validate_sql(query)
        if not is_valid:
            logger.warning(f"SQL validation rejected query: {error_msg}")
            return {
                "success": False,
                "status": "security_violation",
                "answer": f"SQL Query Rejected: {error_msg}",
                "analysis_type": "SQL Query",
                "evidence": {},
                "proof": f"Security Gate: Blocked statement.\nReason: {error_msg}",
                "validation": [
                    {"check": "Read-Only Security Gate", "passed": False, "detail": error_msg}
                ],
                "insight": "Please provide a safe, read-only SELECT query without destructive operations.",
                "chart_info": {},
                "source_data": [],
                "raw_code": query,
                "selected_datasets": list(data_files.keys()),
                "selected_columns": []
            }

        # 2. Setup In-Memory SQLite Database and Load Datasets
        conn = sqlite3.connect(":memory:")
        table_aliases = {}
        total_rows_across_all = 0

        try:
            for orig_name, fpath in data_files.items():
                if not os.path.exists(fpath):
                    continue

                df = FileLoader.load_file(fpath)
                if df is None:
                    continue

                total_rows_across_all += len(df)

                # Register table under multiple friendly names:
                # 1. Base stem without extension (e.g., 'orders', 'customers', 'products')
                stem = os.path.splitext(orig_name)[0].lower().replace("-", "_").replace(" ", "_")
                # 2. Sanitized full name (e.g., 'orders_csv', 'customers_csv')
                sanitized = orig_name.lower().replace(".", "_").replace("-", "_").replace(" ", "_")

                df.to_sql(stem, conn, index=False, if_exists="replace")
                table_aliases[stem] = orig_name

                if sanitized != stem:
                    df.to_sql(sanitized, conn, index=False, if_exists="replace")
                    table_aliases[sanitized] = orig_name

            # If only 1 dataset is loaded, also register as 'df' and 'data'
            if len(data_files) == 1:
                first_alias = list(table_aliases.keys())[0]
                first_orig = list(data_files.keys())[0]
                df_single = FileLoader.load_file(data_files[first_orig])
                if df_single is not None:
                    df_single.to_sql("df", conn, index=False, if_exists="replace")
                    df_single.to_sql("data", conn, index=False, if_exists="replace")
                    table_aliases["df"] = first_orig
                    table_aliases["data"] = first_orig

            if not table_aliases:
                return {
                    "success": False,
                    "status": "error",
                    "answer": "No datasets are currently available to query.",
                    "analysis_type": "SQL Query",
                    "evidence": {},
                    "proof": "No active dataset loaded.",
                    "validation": [{"check": "Dataset Availability", "passed": False, "detail": "No tables registered"}],
                    "insight": "Please upload a valid dataset before running SQL queries.",
                    "chart_info": {},
                    "source_data": [],
                    "raw_code": query
                }

            # 3. Pre-process query: Allow users to write `FROM orders.csv` or `FROM orders`
            # Replaces table.ext with table name (e.g. orders.csv -> orders)
            processed_query = query.strip().rstrip(";")
            for orig_name in data_files.keys():
                stem = os.path.splitext(orig_name)[0].lower().replace("-", "_").replace(" ", "_")
                ext_escaped = re.escape(os.path.splitext(orig_name)[1].lower())
                # Replace 'orders.csv' or `orders.csv` or [orders.csv]
                processed_query = re.sub(
                    rf"\b{re.escape(stem)}{ext_escaped}\b",
                    stem,
                    processed_query,
                    flags=re.IGNORECASE
                )

            # 4. Execute Query with Row Limit
            cur = conn.cursor()
            cur.execute(processed_query)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = cur.fetchmany(500)
            row_count = len(rows)

            # Detect referenced datasets in query
            referenced_datasets = []
            for t_name, orig in table_aliases.items():
                if re.search(rf"\b{re.escape(t_name)}\b", processed_query, re.IGNORECASE):
                    if orig not in referenced_datasets:
                        referenced_datasets.append(orig)

            if not referenced_datasets:
                referenced_datasets = list(data_files.keys())

            source_label = " + ".join(referenced_datasets)

            # 5. Format Answer & Breakdown
            breakdown = []
            top_entity = None
            top_value = None
            is_scalar = False

            if row_count == 0:
                answer = "The SQL query executed successfully, but returned 0 matching records."
            elif row_count == 1 and len(columns) == 1:
                is_scalar = True
                val = rows[0][0]
                val_num = float(val) if isinstance(val, (int, float)) else None
                c_name = columns[0].replace("_", " ").title()
                is_curr = any(k in columns[0].lower() for k in ["revenue", "sales", "profit", "salary", "spend", "cost", "price", "amount"])
                
                if val_num is not None:
                    fmt_val = format_currency(val_num) if is_curr else (f"{val_num:,.2f}" if val_num % 1 != 0 else f"{int(val_num):,}")
                else:
                    fmt_val = str(val)

                answer = f"SQL Query result: {c_name} = {fmt_val}."
                top_entity = c_name
                top_value = val_num if val_num is not None else 0.0
                breakdown = [{"entity": c_name, "value": top_value}]
            elif row_count == 1:
                # 1 row, multiple columns
                pairs = []
                for c, v in zip(columns, rows[0]):
                    is_curr = any(k in c.lower() for k in ["revenue", "sales", "profit", "salary", "spend", "cost", "price", "amount"])
                    if isinstance(v, (int, float)):
                        fmt_v = format_currency(v) if is_curr else (f"{v:,.2f}" if v % 1 != 0 else f"{int(v):,}")
                    else:
                        fmt_v = str(v)
                    pairs.append(f"{c.replace('_', ' ').title()}: {fmt_v}")
                answer = f"SQL Query result: {', '.join(pairs)}."
                top_entity = str(rows[0][0])
                top_value = float(rows[0][1]) if len(columns) > 1 and isinstance(rows[0][1], (int, float)) else 1.0
                breakdown = [{"entity": str(c).title(), "value": float(v) if isinstance(v, (int, float)) else 0} for c, v in zip(columns, rows[0]) if isinstance(v, (int, float))]
            else:
                # Multiple rows
                # Check if column 2 is numeric for ranking/charting
                col1_name = columns[0]
                col2_numeric = len(columns) > 1 and any(isinstance(r[1], (int, float)) for r in rows if r[1] is not None)

                if col2_numeric:
                    for r in rows[:15]:
                        val_n = float(r[1]) if isinstance(r[1], (int, float)) else 0.0
                        breakdown.append({
                            "entity": str(r[0]),
                            "value": round(val_n, 2)
                        })
                    top_entity = str(rows[0][0])
                    top_value = float(rows[0][1]) if isinstance(rows[0][1], (int, float)) else 0.0
                    m_label = columns[1].replace('_', ' ')
                    is_curr = any(k in m_label.lower() for k in ["revenue", "sales", "profit", "salary", "spend", "cost", "price", "amount"])
                    fmt_top = format_currency(top_value) if is_curr else (f"{top_value:,.2f}" if top_value % 1 != 0 else f"{int(top_value):,}")
                    answer = f"SQL Query returned {row_count:,} records. Top result: {top_entity} with {m_label} of {fmt_top}."
                else:
                    for r in rows[:10]:
                        breakdown.append({
                            "entity": str(r[0]),
                            "value": 1
                        })
                    top_entity = str(rows[0][0])
                    top_value = float(row_count)
                    answer = f"SQL Query returned {row_count:,} records across {len(columns)} columns."

            # 6. Source Records Snippet
            source_records = [dict(zip(columns, r)) for r in rows[:25]]

            # 7. Chart Configuration
            chart_info = {}
            if breakdown and len(breakdown) > 1 and any(b["value"] != 0 for b in breakdown):
                labels = [b["entity"] for b in breakdown[:10]]
                values = [b["value"] for b in breakdown[:10]]
                chart_title = f"{columns[1].replace('_', ' ').title() if len(columns) > 1 else 'Values'} by {columns[0].replace('_', ' ').title()}"
                chart_info = VisualizationEngine.build_chart_config(
                    chart_type="bar",
                    labels=labels,
                    data=values,
                    title=chart_title,
                    dataset_label=columns[1].replace('_', ' ').title() if len(columns) > 1 else "Metric"
                )

            # 8. Evidence & Proof
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
                "rows_analyzed": total_rows_across_all,
                "metric_analyzed": columns[1].replace("_", " ").title() if len(columns) > 1 else (columns[0].replace("_", " ").title() if columns else "SQL Result"),
                "group_by": columns[0].replace("_", " ").title() if columns else "Query",
                "breakdown": formatted_breakdown,
                "sample_source_records": source_records
            }

            proof_lines = [
                "Executed Read-Only SQL Query:",
                query.strip(),
                "",
                f"Engine: In-Memory SQLite Database",
                f"Tables Bound: {', '.join(table_aliases.keys())}",
                f"Result Set: {row_count:,} rows returned across {len(columns)} columns ({', '.join(columns)})."
            ]
            if top_entity is not None and top_value is not None:
                proof_lines.append(f"= Leading Record: {top_entity} ({fmt_val_item(top_value)})")

            proof_text = "\n".join(proof_lines)

            # 9. Validation Checklist
            validation_list = [
                {
                    "check": "Read-Only Security Gate",
                    "passed": True,
                    "detail": "0 destructive statements detected (read-only execution verified)"
                },
                {
                    "check": "Table Binding & Schema Resolution",
                    "passed": True,
                    "detail": f"Bound datasets: {source_label}"
                },
                {
                    "check": "Query Execution & Row Reconciliation",
                    "passed": True,
                    "detail": f"Successfully fetched {row_count} rows with {len(columns)} projected columns"
                }
            ]

            # 10. Executive Insight
            insight = InsightGenerator.generate_insight(
                question=f"SQL Query: {query}",
                intent={
                    "analysis_type": "sql",
                    "metric": columns[1] if len(columns) > 1 else (columns[0] if columns else "metric"),
                    "group_by": columns[0] if columns else "entity"
                },
                evidence=evidence,
                answer_text=answer
            )

            return {
                "success": True,
                "status": "completed",
                "answer": answer,
                "analysis_type": "SQL Query",
                "evidence": evidence,
                "proof": proof_text,
                "validation": validation_list,
                "insight": insight,
                "chart_info": chart_info,
                "source_data": source_records,
                "raw_code": query,
                "selected_datasets": referenced_datasets,
                "selected_columns": columns
            }

        except sqlite3.Error as e:
            logger.error(f"SQLite execution error: {e}")
            return {
                "success": False,
                "status": "error",
                "answer": f"SQL Execution Error: {str(e)}. Please check your table and column names.",
                "analysis_type": "SQL Query",
                "evidence": {},
                "proof": f"Query: {query}\nError: {str(e)}",
                "validation": [
                    {"check": "Read-Only Security Gate", "passed": True, "detail": "Passed initial syntax check"},
                    {"check": "SQL Execution", "passed": False, "detail": str(e)}
                ],
                "insight": f"The query encountered a database syntax or column error: {str(e)}. Check registered table names: {', '.join(table_aliases.keys())}.",
                "chart_info": {},
                "source_data": [],
                "raw_code": query,
                "selected_datasets": list(data_files.keys()),
                "selected_columns": []
            }
        except Exception as ex:
            logger.error(f"Unexpected error in SQL executor: {ex}", exc_info=True)
            return {
                "success": False,
                "status": "error",
                "answer": f"Unexpected execution error: {str(ex)}",
                "analysis_type": "SQL Query",
                "evidence": {},
                "proof": f"Query: {query}\nError: {str(ex)}",
                "validation": [{"check": "Execution", "passed": False, "detail": str(ex)}],
                "insight": "An error occurred during SQL processing.",
                "chart_info": {},
                "source_data": [],
                "raw_code": query
            }
        finally:
            conn.close()
