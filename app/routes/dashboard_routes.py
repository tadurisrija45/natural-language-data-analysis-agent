from datetime import datetime
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ..services.activity_service import ActivityService

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    """
    Main user dashboard showing dynamic activity metrics,
    how-it-works cards, and recent analyses.
    """
    metrics = ActivityService.get_user_metrics(current_user.id)
    recent_analyses = ActivityService.get_recent_analyses(current_user.id, limit=6)

    # Dynamic greeting based on current time
    hour = datetime.now().hour
    if hour < 12:
        greeting_time = "Good morning"
    elif hour < 17:
        greeting_time = "Good afternoon"
    else:
        greeting_time = "Good evening"

    greeting = f"{greeting_time}, {current_user.display_name} 👋"

    return render_template(
        "dashboard/dashboard.html",
        greeting=greeting,
        metrics=metrics,
        recent_analyses=recent_analyses
    )
