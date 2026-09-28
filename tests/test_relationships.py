import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
import pandas as pd
from app.analysis.relationship_detector import RelationshipDetector

class TestRelationships(unittest.TestCase):
    def test_relationship_detection(self):
        customers = pd.DataFrame({
            "customer_id": ["C1", "C2", "C3"],
            "name": ["Alice", "Bob", "Charlie"]
        })
        orders = pd.DataFrame({
            "order_id": ["O1", "O2", "O3", "O4"],
            "customer_id": ["C1", "C2", "C1", "C3"],
            "amount": [100, 200, 150, 300]
        })

        dfs = {"customers.csv": customers, "orders.csv": orders}
        rels = RelationshipDetector.detect_relationships(dfs)

        self.assertGreaterEqual(len(rels), 1)
        rel = rels[0]
        self.assertEqual(rel["column_a"], "customer_id")
        self.assertEqual(rel["column_b"], "customer_id")
        self.assertTrue(rel["is_pk_a"])  # C1, C2, C3 are unique in customers
        self.assertEqual(rel["confidence"], "high")

if __name__ == "__main__":
    unittest.main()

