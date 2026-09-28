from datetime import datetime, timezone
import json
from ..extensions.database import db

class Dataset(db.Model):
    __tablename__ = "datasets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)           # stored unique filename
    original_name = db.Column(db.String(255), nullable=False)      # original uploaded filename
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.Integer, default=0)                  # in bytes
    file_type = db.Column(db.String(50), default="csv")
    row_count = db.Column(db.Integer, default=0)
    column_count = db.Column(db.Integer, default=0)
    _profile_data = db.Column("profile_data", db.Text, nullable=True) # JSON string
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship("User", back_populates="datasets")
    analysis = db.relationship("Analysis", back_populates="datasets")

    @property
    def profile_data(self) -> dict:
        if self._profile_data:
            try:
                return json.loads(self._profile_data)
            except Exception:
                return {}
        return {}

    @profile_data.setter
    def profile_data(self, val):
        if val is not None:
            self._profile_data = json.dumps(val)
        else:
            self._profile_data = None

    def __repr__(self):
        return f"<Dataset {self.original_name} ({self.row_count} rows)>"
