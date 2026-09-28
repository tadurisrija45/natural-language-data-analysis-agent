import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
import os
import pandas as pd
from app import create_app
from app.analysis.analysis_pipeline import AnalysisPipeline
from app.analysis.profiler import DatasetProfiler

class TestAnalysisPipeline(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Create temporary test CSV
        self.test_csv_path = os.path.join(self.app.config["TEMPORARY_DIR"], "test_sales.csv")
        df = pd.DataFrame({
            "region": ["South", "North", "South", "East", "West"],
            "sales": [500000, 300000, 400000, 200000, 250000]
        })
        df.to_csv(self.test_csv_path, index=False)
        self.df = df
        self.profile = DatasetProfiler.profile_dataframe(df, "test_sales.csv")

    def tearDown(self):
        if os.path.exists(self.test_csv_path):
            os.remove(self.test_csv_path)
        self.app_context.pop()

    def test_pipeline_highest_region_sales(self):
        datasets_meta = {"test_sales.csv": self.profile}
        data_files = {"test_sales.csv": self.test_csv_path}

        res = AnalysisPipeline.execute_pipeline(
            question="Which region generated the highest sales?",
            datasets_meta=datasets_meta,
            data_files=data_files,
            user_id=1
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "completed")
        self.assertIn("South", res["answer"])
        self.assertEqual(res["evidence"]["rows_analyzed"], 5)
        self.assertGreater(len(res["validation"]), 0)
        self.assertIsNotNone(res["proof"])
        self.assertIsNotNone(res["chart_info"])

    def test_out_of_scope_question(self):
        datasets_meta = {"test_sales.csv": self.profile}
        data_files = {"test_sales.csv": self.test_csv_path}

        res = AnalysisPipeline.execute_pipeline(
            question="What is the weather forecast on Mars tomorrow?",
            datasets_meta=datasets_meta,
            data_files=data_files,
            user_id=1
        )
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "out_of_scope")
        self.assertIn("can't answer this reliably", res["answer"])

if __name__ == "__main__":
    unittest.main()

