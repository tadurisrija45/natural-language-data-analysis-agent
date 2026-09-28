from .auth_routes import auth_bp
from .dashboard_routes import dashboard_bp
from .analysis_routes import analysis_bp
from .history_routes import history_bp
from .account_routes import account_bp
from .api_routes import api_bp

__all__ = [
    "auth_bp",
    "dashboard_bp",
    "analysis_bp",
    "history_bp",
    "account_bp",
    "api_bp",
]
