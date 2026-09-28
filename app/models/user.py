from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions.database import db

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    mobile = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    analyses = db.relationship("Analysis", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    reports = db.relationship("Report", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    datasets = db.relationship("Dataset", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def display_name(self) -> str:
        if self.full_name:
            return self.full_name.split()[0]
        return self.username

    def __repr__(self):
        return f"<User {self.username}>"
