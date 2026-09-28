import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from ..utils.constants import ALLOWED_EXTENSIONS
from .storage_service import StorageService

class FileService:
    @staticmethod
    def allowed_file(filename: str) -> bool:
        """Check if file extension is allowed."""
        if not filename or "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[1].lower()
        return ext in ALLOWED_EXTENSIONS

    @staticmethod
    def save_uploaded_file(file_storage, user_id: int):
        """
        Save an uploaded file into user's isolated directory.
        Returns: (saved_path, unique_filename, original_name, file_size, file_type)
        """
        orig_name = secure_filename(file_storage.filename)
        if not orig_name:
            orig_name = f"upload_{uuid.uuid4().hex[:8]}"

        ext = orig_name.rsplit(".", 1)[1].lower() if "." in orig_name else "csv"
        unique_name = f"{uuid.uuid4().hex[:12]}_{orig_name}"

        user_dir = StorageService.get_user_upload_dir(user_id)
        target_path = user_dir / unique_name

        file_storage.save(str(target_path))
        file_size = os.path.getsize(target_path)

        return str(target_path), unique_name, orig_name, file_size, ext
