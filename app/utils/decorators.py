from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
from ..models import Analysis

def user_analysis_required(f):
    """Ensure the requested analysis belongs to the currently logged in user."""
    @wraps(f)
    def decorated_function(analysis_id, *args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        analysis = Analysis.query.filter_by(id=analysis_id, user_id=current_user.id).first()
        if not analysis:
            abort(404, description="Analysis not found or access denied.")
        return f(analysis, *args, **kwargs)
    return decorated_function
