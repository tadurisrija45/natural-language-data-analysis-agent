import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
import pandas as pd
from app.analysis.profiler import DatasetProfiler

class TestProfiler(unittest.TestCase):
    def test_profile_dataframe(self):
        df = pd.DataFrame({
            "region": ["South", "North", "South", "West"],
            "revenue": [1000.0, 2000.0, 1500.0, 500.0],
            "order_date": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"],
            "active": [True, True, False, True]
        })
        profile = DatasetProfiler.profile_dataframe(df, filename="test.csv")

        self.assertEqual(profile["row_count"], 4)
        self.assertEqual(profile["column_count"], 4)
        self.assertIn("revenue", profile["numerical_columns"])
        self.assertIn("region", profile["categorical_columns"])
        self.assertEqual(profile["missing_values"], 0)
        self.assertEqual(profile["duplicate_rows"], 0)

        # Check column details stats
        rev_stats = profile["column_details"]["revenue"]
        self.assertEqual(rev_stats["min"], 500.0)
        self.assertEqual(rev_stats["max"], 2000.0)
        self.assertEqual(rev_stats["sum"], 5000.0)

if __name__ == "__main__":
    unittest.main()

