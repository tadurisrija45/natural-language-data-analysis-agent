from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from ..extensions.database import db
from ..auth.password_service import PasswordService
from ..auth.validators import AuthValidator
from ..services.storage_service import StorageService

account_bp = Blueprint("account", __name__)

@account_bp.route("/account", methods=["GET", "POST"])
@login_required
def profile():
    """
    My Account page showing details, allowing profile edits and password updates.
    """
    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_profile":
            full_name = request.form.get("full_name", "").strip()
            mobile = request.form.get("mobile", "").strip()

            if not full_name or len(full_name) < 2:
                flash("Full name must be at least 2 characters.", "error")
            else:
                current_user.full_name = full_name
                current_user.mobile = mobile
                db.session.commit()
                flash("Profile details updated successfully.", "success")

        elif action == "change_password":
            current_pwd = request.form.get("current_password", "")
            new_pwd = request.form.get("new_password", "")
            confirm_pwd = request.form.get("confirm_password", "")

            if not PasswordService.verify_password(current_user.password_hash, current_pwd):
                flash("Current password is incorrect.", "error")
            else:
                valid, err = AuthValidator.validate_password_reset(new_pwd, confirm_pwd)
                if not valid:
                    flash(err, "error")
                else:
                    current_user.set_password(new_pwd)
                    db.session.commit()
                    flash("Password changed successfully.", "success")

        return redirect(url_for("account.profile"))

    return render_template("account/profile.html", user=current_user)

@account_bp.route("/settings")
@login_required
def settings():
    """
    Settings page covering Account, Analysis Preferences, Storage, and Security.
    """
    storage_stats = StorageService.get_storage_stats(current_user.id)
    return render_template(
        "account/settings.html",
        user=current_user,
        storage_stats=storage_stats
    )
