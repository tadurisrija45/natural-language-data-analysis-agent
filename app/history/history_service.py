from typing import List, Optional
from ..models import Analysis
from ..extensions.database import db

class HistoryService:
    @staticmethod
    def get_user_history(user_id: int) -> List[Analysis]:
        """Return all analysis sessions belonging to the user ordered by recency."""
        return Analysis.query.filter_by(user_id=user_id).order_by(Analysis.created_at.desc()).all()

    @staticmethod
    def get_analysis_by_id(analysis_id: int, user_id: int) -> Optional[Analysis]:
        """Get an analysis ensuring strict user isolation."""
        return Analysis.query.filter_by(id=analysis_id, user_id=user_id).first()

    @staticmethod
    def delete_analysis(analysis_id: int, user_id: int) -> bool:
        """Delete an analysis and cascade delete its datasets, messages, and reports."""
        analysis = Analysis.query.filter_by(id=analysis_id, user_id=user_id).first()
        if not analysis:
            return False
        db.session.delete(analysis)
        db.session.commit()
        return True
