from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..auth.authentication import AuthService
from ..auth.validators import AuthValidator

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    return redirect(url_for("auth.login"))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        is_valid, err = AuthValidator.validate_login(identifier, password)
        if not is_valid:
            flash(err, "error")
            return render_template("auth/login.html", identifier=identifier)

        user, err = AuthService.authenticate(identifier, password)
        if not user:
            flash(err, "error")
            return render_template("auth/login.html", identifier=identifier)

        login_user(user, remember=True)
        flash(f"Welcome back, {user.display_name}!", "success")
        next_page = request.args.get("next")
        return redirect(next_page or url_for("dashboard.dashboard"))

    return render_template("auth/login.html")

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        is_valid, err = AuthValidator.validate_signup(
            full_name, username, email, mobile, password, confirm_password
        )
        if not is_valid:
            flash(err, "error")
            return render_template(
                "auth/signup.html",
                full_name=full_name,
                username=username,
                email=email,
                mobile=mobile
            )

        user, err = AuthService.register_user(full_name, username, email, mobile, password)
        if not user:
            flash(err, "error")
            return render_template(
                "auth/signup.html",
                full_name=full_name,
                username=username,
                email=email,
                mobile=mobile
            )

        flash("Account created successfully! Please log in to proceed.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/signup.html")

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        is_valid, err = AuthValidator.validate_password_reset(new_password, confirm_password)
        if not is_valid:
            flash(err, "error")
            return render_template("auth/forgot_password.html", identifier=identifier)

        success, err = AuthService.reset_password(identifier, new_password)
        if not success:
            flash(err, "error")
            return render_template("auth/forgot_password.html", identifier=identifier)

        flash("Password reset successfully. You can now log in with your new password.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("auth.login"))
