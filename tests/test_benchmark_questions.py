import os
import unittest
import pandas as pd
from app import create_app
from app.analysis.file_loader import FileLoader
from app.analysis.profiler import DatasetProfiler
from app.analysis.analysis_pipeline import AnalysisPipeline

class TestBenchmarkQuestions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        # Load benchmark datasets
        cls.data_files = {
            "customers.csv": os.path.abspath("data/developer/customers.csv"),
            "orders.csv": os.path.abspath("data/developer/orders.csv"),
            "products.xlsx": os.path.abspath("data/developer/products.xlsx")
        }

        cls.datasets_meta = {}
        for name, path in cls.data_files.items():
            df = FileLoader.load_file(path)
            meta = DatasetProfiler.profile_dataframe(df, filename=name)
            cls.datasets_meta[name] = meta

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    def test_q1_region_highest_revenue(self):
        res = AnalysisPipeline.execute_pipeline(
            "Which region generated the highest revenue?",
            self.datasets_meta,
            self.data_files
        )
        self.assertTrue(res["success"])
        self.assertIn("South", res["answer"])
        self.assertTrue(len(res["evidence"]["breakdown"]) > 0)

    def test_q2_product_highest_revenue(self):
        res = AnalysisPipeline.execute_pipeline(
            "Which product generated the highest revenue?",
            self.datasets_meta,
            self.data_files
        )
        self.assertTrue(res["success"])
        self.assertIsNotNone(res["answer"])
        self.assertTrue(len(res["evidence"]["breakdown"]) > 0)

    def test_q3_customer_highest_revenue(self):
        res = AnalysisPipeline.execute_pipeline(
            "Which customer generated the highest revenue?",
            self.datasets_meta,
            self.data_files
        )
        self.assertTrue(res["success"])
        self.assertIsNotNone(res["answer"])
        self.assertTrue(len(res["evidence"]["breakdown"]) > 0)

    def test_q4_how_many_customers(self):
        res = AnalysisPipeline.execute_pipeline(
            "How many customers are there?",
            self.datasets_meta,
            self.data_files
        )
        self.assertTrue(res["success"])
        self.assertIn("15", res["answer"])
        self.assertNotIn("generated the highest", res["answer"])

    def test_q5_customer_segment_highest_revenue(self):
        res = AnalysisPipeline.execute_pipeline(
            "Which customer segment generated the highest revenue?",
            self.datasets_meta,
            self.data_files
        )
        self.assertTrue(res["success"])
        self.assertIsNotNone(res["answer"])
        self.assertTrue(len(res["evidence"]["breakdown"]) > 0)

    def test_q6_highest_profit_margin(self):
        res = AnalysisPipeline.execute_pipeline(
            "Which product has the highest profit margin?",
            self.datasets_meta,
            self.data_files
        )
        self.assertTrue(res["success"])
        self.assertIsNotNone(res["answer"])
        self.assertIn("%", res["answer"])

    def test_q7_total_revenue(self):
        res = AnalysisPipeline.execute_pipeline(
            "What is the total revenue?",
            self.datasets_meta,
            self.data_files
        )
        self.assertTrue(res["success"])
        self.assertIn("total", res["answer"].lower())
        self.assertNotIn("generated the highest", res["answer"])

    def test_q8_revenue_over_time(self):
        res = AnalysisPipeline.execute_pipeline(
            "How did revenue change over time?",
            self.datasets_meta,
            self.data_files
        )
        self.assertTrue(res["success"])
        self.assertIsNotNone(res["answer"])
        self.assertTrue(len(res["evidence"]["breakdown"]) > 0)

if __name__ == "__main__":
    unittest.main()
