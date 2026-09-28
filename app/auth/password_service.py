from werkzeug.security import generate_password_hash, check_password_hash

class PasswordService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plain text password using Werkzeug's secure algorithm."""
        return generate_password_hash(password, method="scrypt")

    @staticmethod
    def verify_password(stored_hash: str, password: str) -> bool:
        """Verify plain password against hashed value."""
        if not stored_hash or not password:
            return False
        return check_password_hash(stored_hash, password)
