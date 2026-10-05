import os
from flask import Flask, render_template
from .config.settings import config_by_name
from .extensions.database import db
from .extensions.login_manager import login_manager
from .routes.auth_routes import auth_bp
from .routes.dashboard_routes import dashboard_bp
from .routes.analysis_routes import analysis_bp
from .routes.history_routes import history_bp
from .routes.account_routes import account_bp
from .routes.api_routes import api_bp
from .utils.constants import BRAND_NAME, BRAND_TAGLINE, THEME_COLORS
from .utils.helpers import format_currency, format_number, format_file_size, format_datetime

def create_app(config_name: str = "default") -> Flask:
    """Application factory for DataAgent."""
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Ensure required directories exist
    for dir_key in ["DATA_DIR", "DEVELOPER_DATA_DIR", "USER_UPLOADS_DIR", "STORAGE_DIR", "REPORTS_DIR", "CHARTS_DIR", "TEMPORARY_DIR"]:
        dpath = app.config.get(dir_key)
        if dpath:
            os.makedirs(dpath, exist_ok=True)
            
    db_parent = os.path.dirname(app.config["DB_PATH"])
    os.makedirs(db_parent, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # SQLite WAL mode and busy timeout for high concurrency
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    import sqlite3

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA busy_timeout=60000;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
            except Exception:
                pass
            finally:
                cursor.close()

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        db.session.remove()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(api_bp)

    # Context processors for templates
    @app.context_processor
    def inject_global_vars():
        return {
            "BRAND_NAME": BRAND_NAME,
            "BRAND_TAGLINE": BRAND_TAGLINE,
            "THEME_COLORS": THEME_COLORS,
            "format_currency": format_currency,
            "format_number": format_number,
            "format_file_size": format_file_size,
            "format_datetime": format_datetime,
        }

    # Custom Error Pages
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("analysis/error.html", error_code=404, message="Page not found."), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("analysis/error.html", error_code=500, message="An internal server error occurred."), 500

    # Create tables automatically and ensure schema migrations
    with app.app_context():
        db.create_all()
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if "analysis_messages" in inspector.get_table_names():
                existing_cols = [c["name"] for c in inspector.get_columns("analysis_messages")]
                with db.engine.connect() as conn:
                    if "selected_datasets" not in existing_cols:
                        conn.execute(text("ALTER TABLE analysis_messages ADD COLUMN selected_datasets VARCHAR(255)"))
                    if "selected_columns" not in existing_cols:
                        conn.execute(text("ALTER TABLE analysis_messages ADD COLUMN selected_columns VARCHAR(255)"))
                    if "mode" not in existing_cols:
                        conn.execute(text("ALTER TABLE analysis_messages ADD COLUMN mode VARCHAR(50) DEFAULT 'natural_language'"))
                    if "suggested_questions" not in existing_cols:
                        conn.execute(text("ALTER TABLE analysis_messages ADD COLUMN suggested_questions TEXT"))
                    conn.commit()
        except Exception:
            pass

    return app

