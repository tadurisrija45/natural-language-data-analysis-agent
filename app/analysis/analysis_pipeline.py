import os
from typing import Dict, Any, List, Optional
from flask import current_app

from ..agents.question_analyzer import QuestionAnalyzer
from ..agents.analysis_planner import AnalysisPlanner
from ..agents.code_generator import CodeGenerator
from ..agents.correction_agent import CorrectionAgent
from ..agents.evidence_generator import EvidenceGenerator
from ..agents.insight_generator import InsightGenerator
from .validator import ResultValidator
from .visualization import VisualizationEngine
from .executor import CodeExecutor
from ..utils.logger import get_logger

logger = get_logger("DataAgent.Pipeline")

class AnalysisPipeline:
    @classmethod
    def execute_pipeline(
        cls,
        question: str,
        datasets_meta: Dict[str, Any],
        data_files: Dict[str, str],
        user_id: int = None
    ) -> Dict[str, Any]:
        """
        End-to-End Orchestrated AI Analysis Pipeline:
        1. Question Analyzer
        2. Scope & missing data check
        3. Analysis Planner
        4. Code Generator
        5. Sandbox Execution with Iterative Self-Correction (up to 3 retries)
        6. Result Validator
        7. Evidence & Proof Generator
        8. Chart Generator
        9. Insight Generator
        10. Final Answer Synthesis
        """
        logger.info(f"Initiating analysis pipeline for: '{question}'")

        if not datasets_meta or not data_files:
            return {
                "success": False,
                "status": "error",
                "answer": "No dataset is currently loaded. Please upload at least one dataset to begin analysis.",
                "analysis_type": "Out-of-Scope",
                "evidence": {},
                "proof": "",
                "validation": [],
                "insight": "Please upload a valid tabular dataset (CSV, Excel, JSON, Parquet).",
                "chart_info": {},
                "source_data": []
            }

        # Check for out-of-scope or empty query
        q_clean = (question or "").strip()
        if not q_clean:
            return {
                "success": False,
                "status": "error",
                "answer": "Please enter a valid business question to analyze.",
                "analysis_type": "Invalid Question",
                "evidence": {},
                "proof": "",
                "validation": [],
                "insight": "",
                "chart_info": {},
                "source_data": []
            }

        # Check out-of-scope questions that cannot be answered from datasets
        all_cols = []
        for d in datasets_meta.values():
            all_cols.extend([c.lower() for c in d.get("columns", [])])

        irrelevant_keywords = ["weather", "president", "moon", "recipe", "quantum", "alien", "movie reviews"]
        if any(w in q_clean.lower() for w in irrelevant_keywords) and not any(w in " ".join(all_cols) for w in irrelevant_keywords):
            return {
                "success": False,
                "status": "out_of_scope",
                "answer": "I can't answer this reliably from the uploaded datasets because the required information is not available in your files.",
                "analysis_type": "Out of Scope",
                "evidence": {"source_dataset": list(datasets_meta.keys())[0], "rows_analyzed": 0, "breakdown": []},
                "proof": "Query attributes do not map to uploaded schema.",
                "validation": [
                    {"check": "Dataset check", "passed": True, "detail": "Active datasets inspected"},
                    {"check": "Schema mapping", "passed": False, "detail": "Required domain columns not present in dataset"}
                ],
                "insight": "To answer this question, please upload a dataset containing the relevant subject metrics.",
                "chart_info": {},
                "source_data": []
            }

        # Step 1: Question Analyzer
        intent = QuestionAnalyzer.analyze_question(q_clean, datasets_meta)

        # Step 2: Analysis Planner
        plan = AnalysisPlanner.create_plan(intent, q_clean)

        # Step 3: Code Generator
        code = CodeGenerator.generate_code(intent, plan, datasets_meta)

        # Step 4: Secure Sandbox Execution with Iterative Self-Correction
        max_retries = 3
        attempt = 1
        current_code = code
        exec_res = None

        while attempt <= max_retries:
            exec_res = CodeExecutor.run_analysis_code(
                code=current_code,
                data_files=data_files,
                user_id=user_id
            )
            if exec_res.success and exec_res.result_data and not exec_res.result_data.get("error"):
                logger.info(f"Execution succeeded on attempt {attempt}")
                break

            err_msg = exec_res.error or (exec_res.result_data.get("error") if exec_res.result_data else "Unknown error")
            logger.warning(f"Execution failed on attempt {attempt}: {err_msg}")

            if attempt < max_retries:
                current_code = CorrectionAgent.correct_code(
                    failing_code=current_code,
                    error_message=err_msg,
                    intent=intent,
                    datasets_meta=datasets_meta,
                    attempt_number=attempt
                )
            attempt += 1

        if not exec_res or not exec_res.success or not exec_res.result_data or exec_res.result_data.get("error"):
            err_msg = exec_res.error if exec_res else "Analysis execution failed"
            return {
                "success": False,
                "status": "error",
                "answer": "We couldn't complete this analysis. Please try rephrasing your question or verify dataset columns.",
                "analysis_type": plan.get("friendly_label", "Analysis"),
                "evidence": {},
                "proof": "",
                "validation": [{"check": "Execution", "passed": False, "detail": str(err_msg)}],
                "insight": "An error occurred during computational execution in the sandbox.",
                "chart_info": {},
                "source_data": []
            }

        result_data = exec_res.result_data

        # Step 5: Result Validator
        validation_list = ResultValidator.validate_analysis_result(
            question=q_clean,
            intent=intent,
            raw_result=result_data,
            available_datasets=datasets_meta
        )

        # Step 6: Evidence & Proof Generator
        target_ds_name = intent.get("target_dataset") or list(datasets_meta.keys())[0]
        evidence_pack = EvidenceGenerator.generate_evidence_and_proof(
            intent=intent,
            execution_result=result_data,
            target_dataset_name=target_ds_name
        )
        evidence = evidence_pack["evidence"]
        proof = evidence_pack["proof"]

        # Step 7: Final Answer
        raw_summary = result_data.get("summary")
        top_entity = result_data.get("top_entity")
        top_val = result_data.get("top_value")
        metric_name = intent.get("metric", "value")
        sort_order = intent.get("sort", "descending")
        analysis_type = intent.get("analysis_type", "groupby_aggregation")

        if raw_summary:
            answer = raw_summary
        elif top_entity is not None and top_val is not None:
            formatted_val = evidence["breakdown"][0]["formatted_value"] if evidence["breakdown"] else str(top_val)
            superlative = "lowest" if sort_order == "ascending" else "highest"
            answer = f"{top_entity} generated the {superlative} {metric_name.replace('_', ' ')} with {formatted_val}."
        else:
            answer = f"Analysis completed across {evidence.get('rows_analyzed', 0)} records."

        # Step 8: Chart Generator
        breakdown = result_data.get("breakdown", [])
        chart_info = {}
        # Only render chart if there are multiple entities to compare
        if breakdown and len(breakdown) > 1 and intent.get("chart_type"):
            labels = [str(b["entity"]) for b in breakdown[:10]]
            values = [float(b["value"]) for b in breakdown[:10]]
            chart_type = intent.get("chart_type", "bar")
            g_title = intent.get('group_by', 'Category') or 'Category'
            m_title = intent.get('metric', 'Metric') or 'Metric'
            chart_title = f"{m_title.replace('_', ' ').title()} by {g_title.replace('_', ' ').title()}"

            chart_config = VisualizationEngine.build_chart_config(
                chart_type=chart_type,
                labels=labels,
                data=values,
                title=chart_title,
                dataset_label=m_title.replace("_", " ").title()
            )

            # Generate static image for PDF reports
            try:
                static_img_path = VisualizationEngine.render_static_chart_image(
                    chart_type=chart_type,
                    labels=labels,
                    data=values,
                    title=chart_title,
                    dataset_label=m_title.replace("_", " ").title()
                )
                chart_config["static_image_path"] = static_img_path
            except Exception as e:
                logger.warning(f"Could not render static chart image: {e}")
                chart_config["static_image_path"] = None

            chart_info = chart_config

        # Step 9: Insight Generator
        insight = InsightGenerator.generate_insight(
            question=q_clean,
            intent=intent,
            evidence=evidence,
            answer_text=answer
        )

        return {
            "success": True,
            "status": "completed",
            "answer": answer,
            "analysis_type": plan.get("friendly_label", "Analysis"),
            "evidence": evidence,
            "proof": proof,
            "validation": validation_list,
            "insight": insight,
            "chart_info": chart_info,
            "source_data": result_data.get("source_records", []),
            "raw_code": current_code,
            "selected_datasets": intent.get("selected_datasets", [target_ds_name]),
            "selected_columns": [c for c in [intent.get("group_by"), intent.get("metric")] if c]
        }

