"""
Seed initial demo user and analysis session for quick evaluation.
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions.database import db
from app.models import User, Analysis, Dataset, AnalysisMessage, AnalysisFile
from app.auth.authentication import AuthService
from app.analysis.profiler import DatasetProfiler
from app.analysis.file_loader import FileLoader
from app.analysis.analysis_pipeline import AnalysisPipeline
from app.services.title_generator import TitleGenerator

def seed():
    app = create_app()
    with app.app_context():
        # Check if demo user already exists
        user = User.query.filter_by(username="srija").first()
        if not user:
            user, _ = AuthService.register_user(
                full_name="Srija Patel",
                username="srija",
                email="srija@dataagent.io",
                mobile="+91 98765 43210",
                password="password123"
            )
            print(f"Created demo user: {user.username}")

        # Check if analysis exists for user
        if user.analyses.count() == 0:
            dev_csv = os.path.join(app.config["DEVELOPER_DATA_DIR"], "ecommerce_sales.csv")
            if os.path.exists(dev_csv):
                title, cat, icon = TitleGenerator.generate_title_and_category(["ecommerce_sales.csv"], "Regional Sales Analysis")
                analysis = Analysis(
                    user_id=user.id,
                    title="Regional Sales Performance Analysis",
                    category="sales",
                    icon="📊",
                    status="Completed"
                )
                db.session.add(analysis)
                db.session.flush()

                df = FileLoader.load_file(dev_csv)
                profile = DatasetProfiler.profile_dataframe(df, "ecommerce_sales.csv")

                ds = Dataset(
                    user_id=user.id,
                    analysis_id=analysis.id,
                    filename="ecommerce_sales.csv",
                    original_name="ecommerce_sales.csv",
                    file_path=dev_csv,
                    file_size=os.path.getsize(dev_csv),
                    file_type="csv",
                    row_count=profile.get("row_count", 25),
                    column_count=profile.get("column_count", 12)
                )
                ds.profile_data = profile
                db.session.add(ds)
                db.session.flush()

                af = AnalysisFile(
                    analysis_id=analysis.id,
                    dataset_id=ds.id,
                    filename="ecommerce_sales.csv",
                    file_type="csv",
                    file_size=os.path.getsize(dev_csv)
                )
                db.session.add(af)

                # Execute initial question
                pipeline_res = AnalysisPipeline.execute_pipeline(
                    question="Which region generated the highest sales?",
                    datasets_meta={"ecommerce_sales.csv": profile},
                    data_files={"ecommerce_sales.csv": dev_csv},
                    user_id=user.id
                )

                msg = AnalysisMessage(
                    analysis_id=analysis.id,
                    user_id=user.id,
                    message_type="agent",
                    question="Which region generated the highest sales?",
                    answer=pipeline_res.get("answer"),
                    analysis_type=pipeline_res.get("analysis_type"),
                    status="completed",
                    proof=pipeline_res.get("proof"),
                    insight=pipeline_res.get("insight"),
                    raw_code=pipeline_res.get("raw_code")
                )
                msg.evidence = pipeline_res.get("evidence", {})
                msg.validation = pipeline_res.get("validation", [])
                msg.chart_info = pipeline_res.get("chart_info", {})
                msg.source_data = pipeline_res.get("source_data", [])

                db.session.add(msg)
                db.session.commit()
                print("Seeded demo analysis session and question for Srija!")

if __name__ == "__main__":
    seed()
