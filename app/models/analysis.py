from datetime import datetime, timezone
from ..extensions.database import db

class Analysis(db.Model):
    __tablename__ = "analyses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False, default="Untitled Analysis")
    category = db.Column(db.String(50), default="general")
    icon = db.Column(db.String(10), default="📊")
    status = db.Column(db.String(50), default="Active")  # Active, Completed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship("User", back_populates="analyses")
    datasets = db.relationship("Dataset", back_populates="analysis", cascade="all, delete-orphan", lazy="selectin")
    analysis_files = db.relationship("AnalysisFile", back_populates="analysis", cascade="all, delete-orphan", lazy="selectin")
    messages = db.relationship("AnalysisMessage", back_populates="analysis", cascade="all, delete-orphan", order_by="AnalysisMessage.created_at.asc()", lazy="selectin")
    reports = db.relationship("Report", back_populates="analysis", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def question_count(self) -> int:
        return sum(1 for m in self.messages if m.message_type == "user" or m.question)

    @property
    def dataset_count(self) -> int:
        return len(self.datasets)

    def __repr__(self):
        return f"<Analysis {self.id}: {self.title}>"
