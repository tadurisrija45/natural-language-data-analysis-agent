from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_file
from flask_login import login_required, current_user

from ..models import Analysis
from ..history.history_service import HistoryService
from ..history.search_service import SearchService
from ..reports.report_service import ReportService

history_bp = Blueprint("history", __name__)

@history_bp.route("/history")
@login_required
def history():
    """
    Searchable history list of analysis sessions.
    """
    q = request.args.get("q", "").strip()
    if q:
        analyses = SearchService.search_analyses(q, current_user.id)
    else:
        analyses = HistoryService.get_user_history(current_user.id)

    return render_template(
        "history/history.html",
        analyses=analyses,
        search_query=q
    )

@history_bp.route("/history/<int:analysis_id>")
@login_required
def view_analysis(analysis_id):
    """
    View saved analysis details and history from History section.
    """
    analysis = HistoryService.get_analysis_by_id(analysis_id, current_user.id)
    if not analysis:
        flash("Analysis session not found or unauthorized.", "error")
        return redirect(url_for("history.history"))

    return render_template(
        "history/view_analysis.html",
        analysis=analysis,
        datasets=analysis.datasets,
        messages=analysis.messages
    )

@history_bp.route("/history/<int:analysis_id>/pdf")
@login_required
def download_pdf(analysis_id):
    """
    Generate and stream full PDF report for an analysis session.
    """
    import os
    analysis = HistoryService.get_analysis_by_id(analysis_id, current_user.id)
    if not analysis:
        flash("Analysis session not found or unauthorized.", "error")
        return redirect(url_for("history.history"))

    try:
        report = ReportService.get_or_create_report(analysis, current_user)
        if not report or not report.file_path or not os.path.exists(report.file_path):
            flash("Could not generate PDF report at this time.", "warning")
            return redirect(url_for("history.history"))

        safe_title = "".join(c for c in analysis.title if c.isalnum() or c in (" ", "_", "-")).rstrip()
        safe_title = safe_title.replace(" ", "_") or "Report"
        return send_file(
            report.file_path,
            as_attachment=True,
            download_name=f"DataAgent_{safe_title}_{analysis.id}.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        flash(f"Error generating PDF report: {str(e)}", "error")
        return redirect(url_for("history.history"))


@history_bp.route("/history/<int:analysis_id>/delete", methods=["POST"])
@login_required
def delete_analysis(analysis_id):
    """
    Cascade delete an analysis session.
    """
    success = HistoryService.delete_analysis(analysis_id, current_user.id)
    if success:
        flash("Analysis session deleted successfully.", "success")
    else:
        flash("Could not delete analysis session.", "error")
    return redirect(url_for("history.history"))
