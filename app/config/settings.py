import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory is project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dataagent-secret-key-prod-2026-teal")
    
    # Database
    DB_PATH = BASE_DIR / "database" / "app.db"
    db_env_url = os.getenv("DATABASE_URL", "")
    if db_env_url.startswith("sqlite:///"):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH.as_posix()}"
    elif db_env_url:
        SQLALCHEMY_DATABASE_URI = db_env_url
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH.as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "timeout": 60,
            "check_same_thread": False,
        },
        "pool_pre_ping": True,
    }

    # Uploads & Storage
    DATA_DIR = BASE_DIR / "data"
    DEVELOPER_DATA_DIR = DATA_DIR / "developer"
    USER_UPLOADS_DIR = DATA_DIR / "user_uploads"
    
    STORAGE_DIR = BASE_DIR / "storage"
    REPORTS_DIR = STORAGE_DIR / "reports"
    CHARTS_DIR = STORAGE_DIR / "charts"
    TEMPORARY_DIR = STORAGE_DIR / "temporary"
    
    # File limits
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 250 * 1024 * 1024))  # 250 MB
    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "json", "parquet"}

    # Sandbox execution
    USE_DOCKER_SANDBOX = os.getenv("USE_DOCKER_SANDBOX", "false").lower() in ("true", "1", "yes")
    SANDBOX_TIMEOUT_SECONDS = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "60"))
    SANDBOX_MAX_MEMORY_MB = int(os.getenv("SANDBOX_MAX_MEMORY_MB", "1024"))
    MAX_SELF_CORRECTION_RETRIES = 3

    # AI Integration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
