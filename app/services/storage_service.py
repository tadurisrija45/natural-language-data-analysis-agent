import os
import shutil
from pathlib import Path
from flask import current_app

class StorageService:
    @staticmethod
    def get_user_upload_dir(user_id: int) -> Path:
        """Return and create the user-isolated upload directory."""
        base = Path(current_app.config["USER_UPLOADS_DIR"]) / str(user_id)
        base.mkdir(parents=True, exist_ok=True)
        return base

    @staticmethod
    def get_reports_dir() -> Path:
        base = Path(current_app.config["REPORTS_DIR"])
        base.mkdir(parents=True, exist_ok=True)
        return base

    @staticmethod
    def get_charts_dir() -> Path:
        base = Path(current_app.config["CHARTS_DIR"])
        base.mkdir(parents=True, exist_ok=True)
        return base

    @staticmethod
    def get_temporary_dir() -> Path:
        base = Path(current_app.config["TEMPORARY_DIR"])
        base.mkdir(parents=True, exist_ok=True)
        return base

    @staticmethod
    def get_storage_stats(user_id: int) -> dict:
        """Calculate total storage used by user."""
        user_dir = Path(current_app.config["USER_UPLOADS_DIR"]) / str(user_id)
        total_size = 0
        file_count = 0
        if user_dir.exists():
            for root, _, files in os.walk(user_dir):
                for f in files:
                    fp = os.path.join(root, f)
                    total_size += os.path.getsize(fp)
                    file_count += 1
        return {
            "total_bytes": total_size,
            "file_count": file_count,
        }
