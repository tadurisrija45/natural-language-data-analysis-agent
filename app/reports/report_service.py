import os
from typing import Optional
from ..extensions.database import db
from ..models import Analysis, Report, User
from .pdf_generator import PDFReportGenerator

class ReportService:
    @staticmethod
    def get_or_create_report(analysis: Analysis, user: User) -> Report:
        """
        Generate session PDF report and persist record in database.
        """
        pdf_path = PDFReportGenerator.generate_session_report(analysis, user)
        file_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
        filename = os.path.basename(pdf_path)

        # Check existing report for this session
        report = Report.query.filter_by(analysis_id=analysis.id, user_id=user.id).first()
        if report:
            report.filename = filename
            report.file_path = pdf_path
            report.file_size = file_size
        else:
            report = Report(
                analysis_id=analysis.id,
                user_id=user.id,
                filename=filename,
                file_path=pdf_path,
                file_size=file_size
            )
            db.session.add(report)

        db.session.commit()
        return report
