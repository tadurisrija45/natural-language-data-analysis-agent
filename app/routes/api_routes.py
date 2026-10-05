from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user

from ..extensions.database import db
from ..models import Analysis, Dataset, AnalysisMessage
from ..analysis.analysis_pipeline import AnalysisPipeline
from ..analysis.sql_executor import SQLExecutor
from ..analysis.python_executor import PythonExecutor
from ..agents.suggestion_generator import SuggestionGenerator
from ..services.title_generator import TitleGenerator
from ..utils.logger import get_logger

logger = get_logger("DataAgent.API")
api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/analysis/<int:analysis_id>/ask", methods=["POST"])
@api_bp.route("/analysis/<int:analysis_id>/question", methods=["POST"])
@login_required
def ask_question(analysis_id):
    """
    AJAX endpoint for submitting a question, SQL query, or Python code in an active analysis session.
    Supports 3 modes:
      - 'natural_language': Full agentic pipeline (Analyzer -> Planner -> CodeGen -> Sandbox -> Validator -> Insight)
      - 'sql': Direct read-only SQL query execution with automatic Chart & Insight generation
      - 'python': Sandbox execution of user-supplied Python analysis code
    Also generates 3-4 context-aware next-question suggestions.
    """
    analysis = Analysis.query.filter_by(id=analysis_id, user_id=current_user.id).first()
    if not analysis:
        return jsonify({"success": False, "error": "Analysis session not found or unauthorized."}), 404

    data = request.get_json() or {}
    mode = (data.get("mode") or "natural_language").strip().lower()

    # Extract input according to mode
    if mode == "sql":
        input_text = (data.get("query") or data.get("question") or data.get("code") or "").strip()
        if not input_text:
            return jsonify({"success": False, "error": "Please enter a SQL query."}), 400
    elif mode == "python":
        input_text = (data.get("code") or data.get("question") or "").strip()
        if not input_text:
            return jsonify({"success": False, "error": "Please enter Python code."}), 400
    else:
        mode = "natural_language"
        input_text = (data.get("question") or "").strip()
        if not input_text:
            return jsonify({"success": False, "error": "Please enter a business question."}), 400

    # Build dataset maps for executors
    datasets_meta = {}
    data_files = {}

    for ds in analysis.datasets:
        datasets_meta[ds.original_name] = ds.profile_data
        data_files[ds.original_name] = ds.file_path

    # Route execution based on selected mode
    if mode == "sql":
        pipeline_result = SQLExecutor.execute_sql(
            query=input_text,
            data_files=data_files,
            datasets_meta=datasets_meta,
            user_id=current_user.id
        )
    elif mode == "python":
        pipeline_result = PythonExecutor.execute_python(
            code=input_text,
            data_files=data_files,
            datasets_meta=datasets_meta,
            user_id=current_user.id
        )
    else:
        pipeline_result = AnalysisPipeline.execute_pipeline(
            question=input_text,
            datasets_meta=datasets_meta,
            data_files=data_files,
            user_id=current_user.id
        )

    # Gather session question history for suggestion deduplication
    session_history = [m.question for m in analysis.messages if m.question]

    # Generate 3-4 next-question suggestions
    suggested_questions = []
    if pipeline_result.get("success", False):
        try:
            suggested_questions = SuggestionGenerator.generate_suggestions(
                current_input=input_text,
                current_result=pipeline_result,
                datasets_meta=datasets_meta,
                session_history=session_history,
                mode=mode
            )
        except Exception as ex:
            logger.warning(f"Error generating follow-up suggestions: {ex}")
            suggested_questions = []

    # Persist message in database
    message = AnalysisMessage(
        analysis_id=analysis.id,
        user_id=current_user.id,
        message_type="agent",
        mode=mode,
        question=input_text,
        answer=pipeline_result.get("answer"),
        analysis_type=pipeline_result.get("analysis_type"),
        status=pipeline_result.get("status", "completed"),
        proof=pipeline_result.get("proof"),
        insight=pipeline_result.get("insight"),
        raw_code=pipeline_result.get("raw_code") or input_text
    )
    message.evidence = pipeline_result.get("evidence", {})
    message.validation = pipeline_result.get("validation", [])
    message.chart_info = pipeline_result.get("chart_info", {})
    message.source_data = pipeline_result.get("source_data", [])
    message.selected_datasets = pipeline_result.get("selected_datasets", [])
    message.selected_columns = pipeline_result.get("selected_columns", [])
    message.suggested_questions = suggested_questions

    try:
        db.session.add(message)

        # Update session title if this is the first question
        if analysis.question_count <= 1:
            ds_names = [d.original_name for d in analysis.datasets]
            new_title, new_cat, new_icon = TitleGenerator.generate_title_and_category(ds_names, input_text)
            analysis.title = new_title
            analysis.category = new_cat
            analysis.icon = new_icon

        analysis.status = "Completed"
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error persisting question/answer message: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"Failed to save message: {str(e)}"}), 500

    return jsonify({
        "success": True,
        "message": message.to_dict(),
        "analysis_title": analysis.title,
        "analysis_icon": analysis.icon
    })

@api_bp.route("/message/<int:message_id>/source-data", methods=["GET"])
@login_required
def get_source_data(message_id):
    """
    Return representative source data rows for the 'View Source Data' modal.
    """
    message = AnalysisMessage.query.get_or_404(message_id)
    # Check ownership
    if message.analysis.user_id != current_user.id:
        return jsonify({"success": False, "error": "Access denied"}), 403

    return jsonify({
        "success": True,
        "source_dataset": message.evidence.get("source_dataset", "Uploaded Dataset"),
        "rows_analyzed": message.evidence.get("rows_analyzed", 0),
        "columns": list(message.source_data[0].keys()) if message.source_data else [],
        "records": message.source_data
    })
