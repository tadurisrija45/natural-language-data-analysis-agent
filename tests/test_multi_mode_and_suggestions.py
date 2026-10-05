import unittest
import os
import json
import tempfile
import pandas as pd
from unittest.mock import patch

from app import create_app
from app.extensions.database import db
from app.models import User, Analysis, Dataset, AnalysisMessage
from app.analysis.sql_executor import SQLExecutor
from app.analysis.python_executor import PythonExecutor
from app.agents.suggestion_generator import SuggestionGenerator


class TestMultiModeAndSuggestions(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Temporary CSV test files
        self.temp_dir = tempfile.mkdtemp()
        self.orders_path = os.path.join(self.temp_dir, "orders.csv")
        self.customers_path = os.path.join(self.temp_dir, "customers.csv")

        orders_df = pd.DataFrame({
            "order_id": [101, 102, 103, 104, 105],
            "customer_id": [1, 2, 1, 3, 2],
            "category": ["Electronics", "Furniture", "Electronics", "Clothing", "Furniture"],
            "total_amount": [500.0, 150.0, 750.0, 80.0, 300.0],
            "order_date": ["2026-01-10", "2026-01-15", "2026-02-01", "2026-02-10", "2026-03-05"]
        })
        orders_df.to_csv(self.orders_path, index=False)

        customers_df = pd.DataFrame({
            "customer_id": [1, 2, 3],
            "customer_name": ["Alice Smith", "Bob Jones", "Charlie Brown"],
            "region": ["North", "South", "East"]
        })
        customers_df.to_csv(self.customers_path, index=False)

        self.data_files = {
            "orders.csv": self.orders_path,
            "customers.csv": self.customers_path
        }
        self.datasets_meta = {
            "orders.csv": {
                "rows": 5,
                "columns": ["order_id", "customer_id", "category", "total_amount", "order_date"],
                "numerical_columns": ["order_id", "customer_id", "total_amount"],
                "categorical_columns": ["category"],
                "date_columns": ["order_date"]
            },
            "customers.csv": {
                "rows": 3,
                "columns": ["customer_id", "customer_name", "region"],
                "numerical_columns": ["customer_id"],
                "categorical_columns": ["customer_name", "region"],
                "date_columns": []
            }
        }

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # =========================================================
    # 1. SQL Mode Tests
    # =========================================================
    def test_sql_executor_single_table_aggregation(self):
        query = "SELECT category, SUM(total_amount) AS revenue FROM orders GROUP BY category ORDER BY revenue DESC"
        result = SQLExecutor.execute_sql(query, self.data_files, self.datasets_meta)
        self.assertTrue(result["success"])
        self.assertEqual(result["analysis_type"], "SQL Query")
        self.assertIn("Electronics", result["answer"])
        self.assertTrue(len(result["evidence"]["breakdown"]) > 0)
        self.assertTrue(bool(result["chart_info"]))

    def test_sql_executor_multi_table_join(self):
        query = """
            SELECT c.region, SUM(o.total_amount) AS region_revenue
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            GROUP BY c.region
            ORDER BY region_revenue DESC
        """
        result = SQLExecutor.execute_sql(query, self.data_files, self.datasets_meta)
        self.assertTrue(result["success"])
        self.assertIn("region_revenue", [c.lower() for c in result["selected_columns"]])
        self.assertTrue(any(b["entity"] == "North" for b in result["evidence"]["breakdown"]))

    def test_sql_executor_blocks_destructive_statements(self):
        bad_queries = [
            "DROP TABLE orders",
            "DELETE FROM orders WHERE order_id = 101",
            "UPDATE orders SET total_amount = 0",
            "INSERT INTO orders (order_id) VALUES (999)",
            "ALTER TABLE orders ADD COLUMN test INT",
            "TRUNCATE TABLE orders",
            "SELECT * FROM orders; DROP TABLE customers;"
        ]
        for bq in bad_queries:
            result = SQLExecutor.execute_sql(bq, self.data_files, self.datasets_meta)
            self.assertFalse(result["success"], f"Expected query to be rejected: {bq}")
            self.assertEqual(result["status"], "security_violation")

    # =========================================================
    # 2. Python Mode Tests
    # =========================================================
    def test_python_executor_valid_code(self):
        code = """
result = orders.groupby('category')['total_amount'].sum().reset_index()
"""
        result = PythonExecutor.execute_python(code, self.data_files, self.datasets_meta)
        self.assertTrue(result["success"], f"Failed with: {result.get('answer')}")
        self.assertEqual(result["analysis_type"], "Python Script")
        self.assertTrue(len(result["evidence"]["breakdown"]) > 0)

    def test_python_executor_pandas_import_and_read_csv(self):
        code = """
df = pandas.read_csv("orders.csv")
correlation = df["order_id"].corr(df["total_amount"])
print("Order ID vs Total Amount Correlation:", correlation)
"""
        result = PythonExecutor.execute_python(code, self.data_files, self.datasets_meta)
        self.assertTrue(result["success"], f"Failed with: {result.get('answer')}")
        self.assertIn("Correlation", result["answer"])

    def test_python_executor_security_gate_blocks_dangerous_code(self):
        dangerous_codes = [
            "import os; os.system('echo hacked')",
            "import subprocess; subprocess.Popen(['ls'])",
            "open('/etc/passwd', 'r').read()",
            "eval('1 + 1')"
        ]
        for dc in dangerous_codes:
            result = PythonExecutor.execute_python(dc, self.data_files, self.datasets_meta)
            self.assertFalse(result["success"], f"Expected code to be rejected: {dc}")
            self.assertEqual(result["status"], "security_violation")

    # =========================================================
    # 3. AI / Next-Question Suggestions Tests
    # =========================================================
    def test_suggestion_generator_deterministic(self):
        current_input = "Which category generated the highest revenue?"
        current_result = {
            "answer": "Electronics generated the highest revenue of $1,250.00.",
            "evidence": {
                "metric_analyzed": "Total Amount",
                "group_by": "Category",
                "breakdown": [{"entity": "Electronics", "value": 1250.0}]
            }
        }
        suggestions = SuggestionGenerator.generate_suggestions(
            current_input=current_input,
            current_result=current_result,
            datasets_meta=self.datasets_meta,
            session_history=[current_input],
            mode="natural_language"
        )
        self.assertIsInstance(suggestions, list)
        self.assertTrue(3 <= len(suggestions) <= 4)
        # Verify deduplication
        self.assertNotIn(current_input.lower(), [s.lower() for s in suggestions])

    # =========================================================
    # 4. API End-to-End Route Tests with Multi-Mode
    # =========================================================
    def test_api_ask_multi_mode(self):
        # Create test user & analysis
        from app.auth.authentication import AuthService
        user, _ = AuthService.register_user("Test Mode User", "testmodeuser", "testmode@example.com", "12345678", "password123")

        analysis = Analysis(user_id=user.id, title="Test Mode Session")
        db.session.add(analysis)
        db.session.commit()

        ds1 = Dataset(
            user_id=user.id,
            analysis_id=analysis.id,
            filename="orders_test.csv",
            original_name="orders.csv",
            file_path=self.orders_path,
            file_type="csv",
            file_size=100,
            row_count=5,
            column_count=5
        )
        ds1.profile_data = self.datasets_meta["orders.csv"]
        db.session.add(ds1)
        db.session.commit()

        # Login
        self.client.post("/login", data={"identifier": "testmodeuser", "password": "password123"}, follow_redirects=True)

        # 4a. SQL Mode Request
        sql_resp = self.client.post(
            f"/api/analysis/{analysis.id}/ask",
            json={
                "mode": "sql",
                "query": "SELECT category, SUM(total_amount) AS revenue FROM orders GROUP BY category"
            }
        )
        sql_data = sql_resp.get_json()
        self.assertTrue(sql_data["success"])
        self.assertEqual(sql_data["message"]["mode"], "sql")
        self.assertTrue(len(sql_data["message"]["suggested_questions"]) >= 3)

        # 4b. Python Mode Request
        py_resp = self.client.post(
            f"/api/analysis/{analysis.id}/ask",
            json={
                "mode": "python",
                "code": "result = orders['total_amount'].sum()"
            }
        )
        py_data = py_resp.get_json()
        self.assertTrue(py_data["success"])
        self.assertEqual(py_data["message"]["mode"], "python")
        self.assertTrue(len(py_data["message"]["suggested_questions"]) >= 3)


if __name__ == "__main__":
    unittest.main()
