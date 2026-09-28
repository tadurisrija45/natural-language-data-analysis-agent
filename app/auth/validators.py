import re
from typing import Tuple, Optional
from ..models import User

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,30}$")

class AuthValidator:
    @staticmethod
    def validate_signup(
        full_name: str,
        username: str,
        email: str,
        mobile: str,
        password: str,
        confirm_password: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate registration form fields."""
        if not full_name or len(full_name.strip()) < 2:
            return False, "Full name must be at least 2 characters long."

        username = (username or "").strip()
        if not USERNAME_REGEX.match(username):
            return False, "Username must be 3-30 characters and contain only letters, numbers, or underscores."

        email = (email or "").strip().lower()
        if not EMAIL_REGEX.match(email):
            return False, "Please enter a valid email address."

        if not mobile or len(mobile.strip()) < 7:
            return False, "Please enter a valid mobile number."

        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters long."

        if password != confirm_password:
            return False, "Passwords do not match."

        # Check existing user
        if User.query.filter_by(username=username).first():
            return False, "This username is already taken. Please choose another."

        if User.query.filter_by(email=email).first():
            return False, "An account with this email already exists."

        return True, None

    @staticmethod
    def validate_login(identifier: str, password: str) -> Tuple[bool, Optional[str]]:
        """Validate login fields."""
        if not identifier or not identifier.strip():
            return False, "Please enter your username or email."
        if not password:
            return False, "Please enter your password."
        return True, None

    @staticmethod
    def validate_password_reset(password: str, confirm_password: str) -> Tuple[bool, Optional[str]]:
        """Validate password reset without OTP."""
        if not password or len(password) < 6:
            return False, "New password must be at least 6 characters long."
        if password != confirm_password:
            return False, "Passwords do not match."
        return True, None
