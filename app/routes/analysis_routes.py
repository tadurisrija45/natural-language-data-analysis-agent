import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user

from ..extensions.database import db
from ..models import Analysis, Dataset, AnalysisFile, AnalysisMessage
from ..services.file_service import FileService
from ..services.title_generator import TitleGenerator
from ..analysis.file_loader import FileLoader
from ..analysis.profiler import DatasetProfiler
from ..utils.helpers import format_file_size, format_datetime

analysis_bp = Blueprint("analysis", __name__)

@analysis_bp.route("/analysis/new", methods=["GET", "POST"])
@login_required
def new_analysis():
    """
    Upload page for single or multiple datasets.
    """
    if request.method == "POST":
        uploaded_files = request.files.getlist("datasets")

        if not uploaded_files or not any(f.filename for f in uploaded_files):
            flash("Please select at least one valid dataset to upload.", "error")
            return render_template("analysis/new_analysis.html")

        # First, process and profile files on disk before touching the database transaction
        prepared_data = []
        for file_storage in uploaded_files:
            if not file_storage or not file_storage.filename:
                continue

            if not FileService.allowed_file(file_storage.filename):
                flash(f"Unsupported file format for '{file_storage.filename}'. Allowed: CSV, Excel, JSON, Parquet.", "warning")
                continue

            target_path, unique_name, orig_name, file_size, ext = FileService.save_uploaded_file(
                file_storage, current_user.id
            )

            # Profile dataset
            df = FileLoader.load_file(target_path)
            profile_dict = DatasetProfiler.profile_dataframe(df, filename=orig_name) if df is not None else {}
            row_count = profile_dict.get("row_count", 0)
            column_count = profile_dict.get("column_count", 0)

            prepared_data.append({
                "unique_name": unique_name,
                "orig_name": orig_name,
                "target_path": target_path,
                "file_size": file_size,
                "ext": ext,
                "row_count": row_count,
                "column_count": column_count,
                "profile_dict": profile_dict,
            })

        if not prepared_data:
            flash("No valid datasets could be uploaded. Please verify the file formats.", "error")
            return render_template("analysis/new_analysis.html")

        file_names = [p["orig_name"] for p in prepared_data]
        title, category, icon = TitleGenerator.generate_title_and_category(file_names)

        # Fast atomic database commit
        try:
            analysis = Analysis(
                user_id=current_user.id,
                title=title,
                category=category,
                icon=icon,
                status="Active"
            )
            db.session.add(analysis)
            db.session.flush()

            for item in prepared_data:
                dataset = Dataset(
                    user_id=current_user.id,
                    analysis_id=analysis.id,
                    filename=item["unique_name"],
                    original_name=item["orig_name"],
                    file_path=item["target_path"],
                    file_size=item["file_size"],
                    file_type=item["ext"],
                    row_count=item["row_count"],
                    column_count=item["column_count"]
                )
                dataset.profile_data = item["profile_dict"]
                db.session.add(dataset)
                db.session.flush()

                af = AnalysisFile(
                    analysis_id=analysis.id,
                    dataset_id=dataset.id,
                    filename=item["orig_name"],
                    file_type=item["ext"],
                    file_size=item["file_size"]
                )
                db.session.add(af)

            db.session.commit()
            return redirect(url_for("analysis.chat_board", analysis_id=analysis.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error persisting analysis: {e}", exc_info=True)
            flash(f"Database error while creating analysis session: {str(e)}", "error")
            return render_template("analysis/new_analysis.html")

    return render_template("analysis/new_analysis.html")

@analysis_bp.route("/analysis/<int:analysis_id>/chat")
@login_required
def chat_board(analysis_id):
    """
    Interactive chat analysis board where user asks multiple questions
    and receives verified, evidence-backed answers.
    """
    analysis = Analysis.query.filter_by(id=analysis_id, user_id=current_user.id).first()
    if not analysis:
        abort(404, description="Analysis not found or unauthorized.")

    return render_template(
        "analysis/chat.html",
        analysis=analysis,
        datasets=analysis.datasets,
        messages=analysis.messages
    )

@analysis_bp.route("/analysis/<int:analysis_id>")
@login_required
def view_analysis(analysis_id):
    """
    View saved analysis details and history.
    """
    analysis = Analysis.query.filter_by(id=analysis_id, user_id=current_user.id).first()
    if not analysis:
        abort(404, description="Analysis not found or unauthorized.")

    return render_template(
        "history/view_analysis.html",
        analysis=analysis,
        datasets=analysis.datasets,
        messages=analysis.messages
    )

@analysis_bp.route("/analysis/<int:analysis_id>/add-dataset", methods=["POST"])
@login_required
def add_dataset(analysis_id):
    """
    Add one or multiple additional datasets to an existing active analysis session.
    Enables comparing datasets directly within the same chat session.
    """
    analysis = Analysis.query.filter_by(id=analysis_id, user_id=current_user.id).first()
    if not analysis:
        flash("Analysis session not found or unauthorized.", "error")
        return redirect(url_for("dashboard.dashboard"))

    uploaded_files = request.files.getlist("datasets")
    if not uploaded_files or not any(f.filename for f in uploaded_files):
        flash("Please select at least one dataset to add.", "warning")
        return redirect(url_for("analysis.chat_board", analysis_id=analysis.id))

    prepared_data = []
    for file_storage in uploaded_files:
        if not file_storage or not file_storage.filename:
            continue

        if not FileService.allowed_file(file_storage.filename):
            flash(f"Unsupported format for '{file_storage.filename}'. Allowed: CSV, Excel, JSON, Parquet.", "warning")
            continue

        target_path, unique_name, orig_name, file_size, ext = FileService.save_uploaded_file(
            file_storage, current_user.id
        )

        df = FileLoader.load_file(target_path)
        profile_dict = DatasetProfiler.profile_dataframe(df, filename=orig_name) if df is not None else {}
        row_count = profile_dict.get("row_count", 0)
        column_count = profile_dict.get("column_count", 0)

        prepared_data.append({
            "unique_name": unique_name,
            "orig_name": orig_name,
            "target_path": target_path,
            "file_size": file_size,
            "ext": ext,
            "row_count": row_count,
            "column_count": column_count,
            "profile_dict": profile_dict,
        })

    if not prepared_data:
        return redirect(url_for("analysis.chat_board", analysis_id=analysis.id))

    try:
        added_names = []
        for item in prepared_data:
            dataset = Dataset(
                user_id=current_user.id,
                analysis_id=analysis.id,
                filename=item["unique_name"],
                original_name=item["orig_name"],
                file_path=item["target_path"],
                file_size=item["file_size"],
                file_type=item["ext"],
                row_count=item["row_count"],
                column_count=item["column_count"]
            )
            dataset.profile_data = item["profile_dict"]
            db.session.add(dataset)
            db.session.flush()

            af = AnalysisFile(
                analysis_id=analysis.id,
                dataset_id=dataset.id,
                filename=item["orig_name"],
                file_type=item["ext"],
                file_size=item["file_size"]
            )
            db.session.add(af)
            added_names.append(item["orig_name"])

        db.session.commit()
        flash(f"Added {len(added_names)} dataset(s) ({', '.join(added_names)}) to this session. You can now analyze and compare them!", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding dataset: {e}", exc_info=True)
        flash(f"Database error while adding dataset: {str(e)}", "error")

    return redirect(url_for("analysis.chat_board", analysis_id=analysis.id))

