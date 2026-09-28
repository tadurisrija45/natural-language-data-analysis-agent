from typing import List
from sqlalchemy import or_
from ..models import Analysis, Dataset, AnalysisMessage

class SearchService:
    @staticmethod
    def search_analyses(query: str, user_id: int) -> List[Analysis]:
        """
        Multi-field search across:
        - Analysis title
        - Dataset names
        - Analysis questions and answers
        Scoped strictly to user_id.
        """
        if not query or not query.strip():
            return Analysis.query.filter_by(user_id=user_id).order_by(Analysis.created_at.desc()).all()

        pattern = f"%{query.strip()}%"

        # 1. Matching titles
        title_matches = Analysis.query.filter(
            Analysis.user_id == user_id,
            Analysis.title.ilike(pattern)
        ).all()

        # 2. Matching datasets
        dataset_matches = Analysis.query.join(Dataset).filter(
            Analysis.user_id == user_id,
            Dataset.original_name.ilike(pattern)
        ).all()

        # 3. Matching questions or answers
        message_matches = AnalysisMessage.query.filter(
            AnalysisMessage.user_id == user_id,
            or_(
                AnalysisMessage.question.ilike(pattern),
                AnalysisMessage.answer.ilike(pattern),
                AnalysisMessage._insight.ilike(pattern)
            )
        ).all()
        # Retrieve the analyses associated with these messages
        message_analysis_ids = {m.analysis_id for m in message_matches}
        message_analyses = Analysis.query.filter(Analysis.id.in_(message_analysis_ids)).all() if message_analysis_ids else []

        # Combine uniquely while preserving recency
        seen_ids = set()
        results = []
        for a in sorted(title_matches + dataset_matches + message_analyses, key=lambda x: x.created_at, reverse=True):
            if a.id not in seen_ids:
                seen_ids.add(a.id)
                results.append(a)

        return results
