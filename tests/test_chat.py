import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
import io
import json
from app import create_app
from app.extensions.database import db
from app.auth.authentication import AuthService
from app.models import Analysis, AnalysisMessage

class TestChat(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

        self.user, _ = AuthService.register_user("Srija Patel", "srija", "srija@test.com", "12345678", "password123")
        self.client.post("/login", data={"identifier": "srija", "password": "password123"}, follow_redirects=True)

        # Upload dataset
        csv_data = b"region,sales,profit\nSouth,900000,180000\nNorth,720000,144000\nWest,640000,128000\nEast,580000,116000\n"
        self.client.post("/analysis/new", data={
            "datasets": [(io.BytesIO(csv_data), "regional_sales.csv")]
        }, content_type="multipart/form-data", follow_redirects=True)
        self.analysis = Analysis.query.filter_by(user_id=self.user.id).first()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_multi_question_in_session(self):
        # Question 1: highest sales region
        res1 = self.client.post(
            f"/api/analysis/{self.analysis.id}/ask",
            json={"question": "Which region generated the highest sales?"}
        )
        data1 = json.loads(res1.data)
        self.assertTrue(data1["success"])
        self.assertIn("South", data1["message"]["answer"])
        self.assertIsNotNone(data1["message"]["evidence"])

        # Question 2 in same session: highest profit region
        res2 = self.client.post(
            f"/api/analysis/{self.analysis.id}/ask",
            json={"question": "Which region generated the highest profit?"}
        )
        data2 = json.loads(res2.data)
        self.assertTrue(data2["success"])
        self.assertIn("South", data2["message"]["answer"])

        # Check total messages in database
        self.assertEqual(len(self.analysis.messages), 2)

if __name__ == "__main__":
    unittest.main()

