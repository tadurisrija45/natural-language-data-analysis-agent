import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from app import create_app
from app.extensions.database import db
from app.models import User
from app.auth.authentication import AuthService
from app.auth.validators import AuthValidator

class TestAuth(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_registration_and_login(self):
        # Register user
        user, err = AuthService.register_user(
            full_name="Srija Patel",
            username="srijap",
            email="srija@example.com",
            mobile="9876543210",
            password="securepassword123"
        )
        self.assertIsNone(err)
        self.assertIsNotNone(user)
        self.assertEqual(user.display_name, "Srija")

        # Verify authentication
        auth_user, auth_err = AuthService.authenticate("srijap", "securepassword123")
        self.assertIsNone(auth_err)
        self.assertIsNotNone(auth_user)
        self.assertEqual(auth_user.id, user.id)

        # Verify email login
        auth_email_user, _ = AuthService.authenticate("srija@example.com", "securepassword123")
        self.assertIsNotNone(auth_email_user)

        # Verify wrong password failure
        fail_user, fail_err = AuthService.authenticate("srijap", "wrongpass")
        self.assertIsNone(fail_user)
        self.assertIsNotNone(fail_err)

    def test_password_reset_without_otp(self):
        user, _ = AuthService.register_user(
            full_name="Srija Patel",
            username="srijap",
            email="srija@example.com",
            mobile="9876543210",
            password="initialpassword"
        )
        # Reset password directly (no OTP)
        success, err = AuthService.reset_password("srija@example.com", "newpassword999")
        self.assertTrue(success)

        # Authenticate with new password
        auth_user, _ = AuthService.authenticate("srijap", "newpassword999")
        self.assertIsNotNone(auth_user)

    def test_signup_validation(self):
        # Mismatched passwords
        is_val, msg = AuthValidator.validate_signup(
            "Srija", "srija", "s@s.com", "12345678", "pass1", "pass2"
        )
        self.assertFalse(is_val)

        # Short password
        is_val, msg = AuthValidator.validate_signup(
            "Srija", "srija", "s@s.com", "12345678", "123", "123"
        )
        self.assertFalse(is_val)

if __name__ == "__main__":
    unittest.main()

