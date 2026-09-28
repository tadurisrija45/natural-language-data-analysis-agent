from typing import Optional, Tuple
from sqlalchemy import or_
from ..extensions.database import db
from ..extensions.login_manager import login_manager
from ..models import User
from .password_service import PasswordService

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None

class AuthService:
    @staticmethod
    def authenticate(identifier: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        """Find user by username or email, verify password."""
        ident = identifier.strip().lower()
        user = User.query.filter(
            or_(User.username.ilike(ident), User.email.ilike(ident))
        ).first()

        if not user:
            return None, "Invalid username/email or password."

        if not PasswordService.verify_password(user.password_hash, password):
            return None, "Invalid username/email or password."

        return user, None

    @staticmethod
    def register_user(full_name: str, username: str, email: str, mobile: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        """Create new user account with secure password hash."""
        try:
            user = User(
                full_name=full_name.strip(),
                username=username.strip().lower(),
                email=email.strip().lower(),
                mobile=mobile.strip()
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return user, None
        except Exception as e:
            db.session.rollback()
            return None, f"Registration failed: {str(e)}"

    @staticmethod
    def reset_password(identifier: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """Reset user password directly without OTP."""
        ident = identifier.strip().lower()
        user = User.query.filter(
            or_(User.username.ilike(ident), User.email.ilike(ident))
        ).first()

        if not user:
            return False, "No account found matching that username or email."

        try:
            user.set_password(new_password)
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, f"Password reset failed: {str(e)}"
