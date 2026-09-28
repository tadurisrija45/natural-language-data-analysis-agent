import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from app.analysis.validator import ResultValidator

class TestValidation(unittest.TestCase):
    def test_validation_checklist(self):
        question = "Which region generated the highest revenue?"
        intent = {
            "analysis_type": "groupby_aggregation",
            "group_by": "region",
            "metric": "revenue",
            "aggregation": "sum",
            "sort": "descending",
            "limit": 1,
            "dataset_name": "sales.csv"
        }
        raw_result = {
            "top_entity": "South",
            "top_value": 900000,
            "breakdown": [{"entity": "South", "value": 900000}]
        }
        available_datasets = {"sales.csv": {}}

        checklist = ResultValidator.validate_analysis_result(
            question, intent, raw_result, available_datasets
        )

        self.assertEqual(len(checklist), 5)
        # All checks must pass
        for item in checklist:
            self.assertTrue(item["passed"], f"Check failed: {item['check']}")

if __name__ == "__main__":
    unittest.main()

