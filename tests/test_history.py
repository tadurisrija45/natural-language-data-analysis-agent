import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from app import create_app
from app.extensions.database import db
from app.auth.authentication import AuthService
from app.models import Analysis, Dataset, AnalysisMessage
from app.history.search_service import SearchService
from app.history.history_service import HistoryService

class TestHistory(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # User A: Srija
        self.user_a, _ = AuthService.register_user("Srija Patel", "srija", "srija@test.com", "12345678", "password123")
        # User B: John
        self.user_b, _ = AuthService.register_user("John Doe", "john", "john@test.com", "87654321", "password456")

        # Create analyses for User A
        self.a1 = Analysis(user_id=self.user_a.id, title="Regional Sales Analysis", icon="📊")
        db.session.add(self.a1)
        db.session.flush()

        ds1 = Dataset(
            user_id=self.user_a.id,
            analysis_id=self.a1.id,
            filename="unique_orders.csv",
            original_name="orders.csv",
            file_path="/dummy/orders.csv",
            row_count=100
        )
        msg1 = AnalysisMessage(
            analysis_id=self.a1.id,
            user_id=self.user_a.id,
            question="Which region generated highest sales?",
            answer="South generated the highest sales with 900000."
        )
        db.session.add_all([ds1, msg1])

        # Create analyses for User B
        self.b1 = Analysis(user_id=self.user_b.id, title="Marketing ROI Analysis", icon="📣")
        db.session.add(self.b1)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_data_isolation(self):
        # User A should only see their analyses
        history_a = HistoryService.get_user_history(self.user_a.id)
        self.assertEqual(len(history_a), 1)
        self.assertEqual(history_a[0].title, "Regional Sales Analysis")

        # User B should only see their analyses
        history_b = HistoryService.get_user_history(self.user_b.id)
        self.assertEqual(len(history_b), 1)
        self.assertEqual(history_b[0].title, "Marketing ROI Analysis")

        # User A cannot retrieve User B's analysis
        isolated_check = HistoryService.get_analysis_by_id(self.b1.id, self.user_a.id)
        self.assertIsNone(isolated_check)

    def test_search_service(self):
        # Search by dataset name
        results = SearchService.search_analyses("orders", self.user_a.id)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, self.a1.id)

        # Search by question keyword
        results_q = SearchService.search_analyses("highest sales", self.user_a.id)
        self.assertEqual(len(results_q), 1)

        # Search User A for User B's keyword should return empty
        results_b = SearchService.search_analyses("ROI", self.user_a.id)
        self.assertEqual(len(results_b), 0)

if __name__ == "__main__":
    unittest.main()

