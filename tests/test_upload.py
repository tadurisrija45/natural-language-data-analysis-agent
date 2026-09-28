import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
import io
from app import create_app
from app.extensions.database import db
from app.auth.authentication import AuthService
from app.models import Analysis, Dataset

class TestUpload(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

        # Create user
        self.user, _ = AuthService.register_user("Srija Patel", "srija", "srija@test.com", "12345678", "password123")

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_multi_dataset_upload(self):
        # Log in
        self.client.post("/login", data={"identifier": "srija", "password": "password123"}, follow_redirects=True)

        data = {
            "datasets": [
                (io.BytesIO(b"customer_id,name\n1,Alice\n2,Bob\n"), "customers.csv"),
                (io.BytesIO(b"order_id,customer_id,amount\n101,1,500\n102,2,700\n"), "orders.csv")
            ]
        }

        resp = self.client.post("/analysis/new", data=data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Check database records created
        analysis = Analysis.query.filter_by(user_id=self.user.id).first()
        self.assertIsNotNone(analysis)
        self.assertEqual(len(analysis.datasets), 2)
        self.assertEqual(analysis.datasets[0].row_count, 2)

if __name__ == "__main__":
    unittest.main()

