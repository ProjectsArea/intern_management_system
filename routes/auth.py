from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from forms import LoginForm
from models import Attendance, Intern, InternTiming, User
from utils import (
    calculate_late_status,
    dashboard_redirect,
    get_trusted_date,
    get_trusted_time_str,
    verify_location,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        return dashboard_redirect(current_user)
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return dashboard_redirect(current_user)

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f"Welcome back, {user.name}!", "success")
            
            # Auto check-in for interns with location
            if user.role == "intern":
                lat = request.form.get("latitude")
                lon = request.form.get("longitude")
                if lat and lon:
                    try:
                        user_lat = float(lat)
                        user_lon = float(lon)
                        _auto_check_in(user, user_lat, user_lon)
                    except (ValueError, TypeError):
                        pass  # Silently fail if invalid coordinates
            
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            return dashboard_redirect(user)
        flash("Invalid email or password.", "danger")
    return render_template("login.html", form=form)


def _auto_check_in(user, latitude, longitude):
    """Automatically check in intern on login if location is valid."""
    intern = Intern.query.filter_by(user_id=user.id).first()
    if not intern:
        return
    
    # Verify location
    location_valid, _ = verify_location(latitude, longitude)
    if not location_valid:
        return
    
    # Check if already checked in today
    today = get_trusted_date()
    existing = Attendance.query.filter_by(intern_id=intern.id, date=today).first()
    if existing and existing.check_in:
        return
    
    current_time = get_trusted_time_str()
    
    # Get intern timing settings
    timing = InternTiming.query.filter_by(intern_id=intern.id).first()
    
    # Check if late
    is_late = calculate_late_status(current_time, timing)
    
    # Create or update attendance record
    if existing:
        existing.check_in = current_time
        existing.check_in_latitude = latitude
        existing.check_in_longitude = longitude
        existing.location_verified = True
        existing.is_late = is_late
        existing.status = "Present"
    else:
        attendance = Attendance(
            intern_id=intern.id,
            date=today,
            check_in=current_time,
            check_in_latitude=latitude,
            check_in_longitude=longitude,
            location_verified=True,
            is_late=is_late,
            status="Present",
        )
        db.session.add(attendance)
    
    db.session.commit()


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
