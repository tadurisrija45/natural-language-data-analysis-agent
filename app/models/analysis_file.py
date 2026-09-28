from datetime import datetime, timezone
from ..extensions.database import db

class AnalysisFile(db.Model):
    __tablename__ = "analysis_files"

    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), default="csv")
    file_size = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    analysis = db.relationship("Analysis", back_populates="analysis_files")
    dataset = db.relationship("Dataset")

    def __repr__(self):
        return f"<AnalysisFile {self.filename}>"
