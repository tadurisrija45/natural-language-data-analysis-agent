from datetime import datetime, timezone
import json
from ..extensions.database import db

class AnalysisMessage(db.Model):
    __tablename__ = "analysis_messages"

    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    message_type = db.Column(db.String(50), default="agent")  # 'user', 'agent', 'system'
    question = db.Column(db.Text, nullable=True)
    answer = db.Column(db.Text, nullable=True)
    analysis_type = db.Column(db.String(100), nullable=True)   # e.g., "Regional revenue comparison", "Ranking"
    _selected_datasets = db.Column("selected_datasets", db.String(255), nullable=True)
    _selected_columns = db.Column("selected_columns", db.String(255), nullable=True)
    status = db.Column(db.String(50), default="completed")     # completed, error, pending

    
    # Traceability & Evidence components stored as structured JSON
    _evidence = db.Column("evidence", db.Text, nullable=True)
    _proof = db.Column("proof", db.Text, nullable=True)
    _validation = db.Column("validation", db.Text, nullable=True)
    _insight = db.Column("insight", db.Text, nullable=True)
    _chart_info = db.Column("chart_info", db.Text, nullable=True)
    _source_data = db.Column("source_data", db.Text, nullable=True) # snippet for View Source Data modal
    
    # Internal execution artifact for auditing
    raw_code = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    analysis = db.relationship("Analysis", back_populates="messages")
    user = db.relationship("User")

    # JSON helper properties with guaranteed safe types
    @property
    def evidence(self):
        default_evidence = {
            "source_dataset": "Uploaded dataset",
            "rows_analyzed": 0,
            "breakdown": [],
            "metric_analyzed": "Value",
            "group_by": "Category"
        }
        if not self._evidence:
            return default_evidence

        try:
            data = json.loads(self._evidence)
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    pass
            if isinstance(data, dict):
                for k, v in default_evidence.items():
                    data.setdefault(k, v)
                return data
            return default_evidence
        except Exception:
            return default_evidence

    @evidence.setter
    def evidence(self, val):
        self._evidence = json.dumps(val) if isinstance(val, (dict, list)) else val

    @property
    def proof(self):
        return self._proof or ""

    @proof.setter
    def proof(self, val):
        self._proof = val

    @property
    def validation(self):
        if self._validation:
            try:
                res = json.loads(self._validation)
                if isinstance(res, str):
                    res = json.loads(res)
                if isinstance(res, list):
                    return res
                return [res]
            except Exception:
                return []
        return []

    @validation.setter
    def validation(self, val):
        self._validation = json.dumps(val) if isinstance(val, (dict, list)) else val

    @property
    def insight(self):
        return self._insight or ""

    @insight.setter
    def insight(self, val):
        self._insight = val

    @property
    def chart_info(self):
        if self._chart_info:
            try:
                res = json.loads(self._chart_info)
                if isinstance(res, str):
                    res = json.loads(res)
                if isinstance(res, dict):
                    return res
                return {}
            except Exception:
                return {}
        return {}

    @chart_info.setter
    def chart_info(self, val):
        self._chart_info = json.dumps(val) if isinstance(val, (dict, list)) else val

    @property
    def source_data(self):
        if self._source_data:
            try:
                res = json.loads(self._source_data)
                if isinstance(res, str):
                    res = json.loads(res)
                if isinstance(res, list):
                    return res
                return []
            except Exception:
                return []
        return []

    @source_data.setter
    def source_data(self, val):
        self._source_data = json.dumps(val) if isinstance(val, (dict, list)) else val

    @property
    def selected_datasets(self):
        if not self._selected_datasets:
            return []
        try:
            res = json.loads(self._selected_datasets)
            return res if isinstance(res, list) else [str(res)]
        except Exception:
            return [s.strip() for s in self._selected_datasets.split(",") if s.strip()]

    @selected_datasets.setter
    def selected_datasets(self, val):
        if isinstance(val, list):
            self._selected_datasets = json.dumps(val)
        else:
            self._selected_datasets = str(val) if val else None

    @property
    def selected_columns(self):
        if not self._selected_columns:
            return []
        try:
            res = json.loads(self._selected_columns)
            return res if isinstance(res, list) else [str(res)]
        except Exception:
            return [s.strip() for s in self._selected_columns.split(",") if s.strip()]

    @selected_columns.setter
    def selected_columns(self, val):
        if isinstance(val, list):
            self._selected_columns = json.dumps(val)
        else:
            self._selected_columns = str(val) if val else None

    def to_dict(self):

        """Serialize for frontend AJAX delivery."""
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "message_type": self.message_type,
            "question": self.question,
            "answer": self.answer,
            "analysis_type": self.analysis_type,
            "selected_datasets": self.selected_datasets,
            "selected_columns": self.selected_columns,
            "status": self.status,
            "evidence": self.evidence,
            "proof": self.proof,
            "validation": self.validation,
            "insight": self.insight,
            "chart_info": self.chart_info,
            "source_data": self.source_data,
            "created_at": self.created_at.strftime("%I:%M %p") if self.created_at else "",
        }

    def __repr__(self):
        return f"<AnalysisMessage {self.id} ({self.status})>"
