import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
import os
from app import create_app
from app.extensions.database import db
from app.auth.authentication import AuthService
from app.models import Analysis, Dataset, AnalysisMessage
from app.reports.report_service import ReportService

class TestReports(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.user, _ = AuthService.register_user("Srija Patel", "srija", "srija@test.com", "12345678", "password123")
        self.analysis = Analysis(user_id=self.user.id, title="Regional Sales Analysis", icon="📊")
        db.session.add(self.analysis)
        db.session.flush()

        ds = Dataset(
            user_id=self.user.id,
            analysis_id=self.analysis.id,
            filename="sales_test.csv",
            original_name="sales.csv",
            file_path="/dummy/sales.csv",
            file_type="csv",
            row_count=100,
            column_count=5
        )
        msg = AnalysisMessage(
            analysis_id=self.analysis.id,
            user_id=self.user.id,
            question="Which region generated highest sales?",
            answer="South generated the highest sales with ₹9,00,000.",
            proof="South = 500000 + 400000 = ₹9,00,000",
            insight="South accounts for the majority of top-line revenue."
        )
        msg.evidence = {
            "source_dataset": "sales.csv",
            "rows_analyzed": 100,
            "breakdown": [
                {"entity": "South", "formatted_value": "₹9,00,000"},
                {"entity": "North", "formatted_value": "₹7,20,000"}
            ]
        }
        msg.validation = [
            {"check": "Correct dataset", "passed": True, "detail": "sales.csv verified"},
            {"check": "Calculation verified", "passed": True, "detail": "Sum verified"}
        ]
        db.session.add_all([ds, msg])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_pdf_report_generation(self):
        report = ReportService.get_or_create_report(self.analysis, self.user)
        self.assertIsNotNone(report)
        self.assertTrue(os.path.exists(report.file_path))
        self.assertGreater(report.file_size, 0)
        self.assertTrue(report.filename.endswith(".pdf"))

if __name__ == "__main__":
    unittest.main()

