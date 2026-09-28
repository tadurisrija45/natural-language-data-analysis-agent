from typing import Dict, Any, List
from ..models import Analysis, Dataset, Report
from ..extensions.database import db

class ActivityService:
    @staticmethod
    def get_user_metrics(user_id: int) -> Dict[str, int]:
        """
        Dynamically calculate user activity metrics from the database.
        Returns: { 'total_analyses': int, 'datasets_used': int, 'reports': int }
        """
        total_analyses = Analysis.query.filter_by(user_id=user_id).count()
        datasets_used = Dataset.query.filter_by(user_id=user_id).count()
        reports = Report.query.filter_by(user_id=user_id).count()

        return {
            "total_analyses": total_analyses,
            "datasets_used": datasets_used,
            "reports": reports,
        }

    @staticmethod
    def get_recent_analyses(user_id: int, limit: int = 5) -> List[Analysis]:
        """Return the user's most recent analysis sessions."""
        return Analysis.query.filter_by(user_id=user_id).order_by(Analysis.created_at.desc()).limit(limit).all()
