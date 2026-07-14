import csv
import io
import os
import uuid
from datetime import datetime
from functools import wraps

from flask import abort, current_app, flash, redirect, url_for
from flask_login import current_user
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from werkzeug.utils import secure_filename

from extensions import db
from models import (
    Attendance,
    Feedback,
    Intern,
    Mentor,
    Project,
    User,
)


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role not in roles:
                flash("You do not have permission to access that page.", "danger")
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def save_upload(file_storage, subfolder, allowed_extensions):
    if not file_storage or not file_storage.filename:
        return None

    if not allowed_file(file_storage.filename, allowed_extensions):
        raise ValueError("Invalid file type.")

    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)

    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(folder, filename)
    file_storage.save(path)
    return f"{subfolder}/{filename}"


def dashboard_redirect(user):
    if user.role == "admin":
        return redirect(url_for("admin.dashboard"))
    if user.role == "mentor":
        return redirect(url_for("mentor.dashboard"))
    if user.role == "intern":
        return redirect(url_for("intern.dashboard"))
    return redirect(url_for("auth.login"))


def get_mentor_choices():
    mentors = Mentor.query.join(User).order_by(User.name).all()
    return [(0, "Unassigned")] + [(m.id, m.user.name) for m in mentors]


def get_intern_choices(mentor_id=None):
    query = Intern.query.join(User)
    if mentor_id:
        query = query.filter(Intern.mentor_id == mentor_id)
    interns = query.order_by(User.name).all()
    return [(i.id, i.user.name) for i in interns]


def get_project_choices(mentor_id=None):
    query = Project.query
    if mentor_id:
        query = query.filter(Project.mentor_id == mentor_id)
    projects = query.order_by(Project.title).all()
    return [(p.id, p.title) for p in projects]


def attendance_percentage(intern_id=None):
    query = Attendance.query
    if intern_id:
        query = query.filter_by(intern_id=intern_id)
    total = query.count()
    if total == 0:
        return 0
    present = query.filter_by(status="Present").count()
    return round((present / total) * 100, 1)


def seed_database():
    """Create default users and sample data on first run."""
    if User.query.filter_by(email="admin@internhub.com").first():
        return

    admin = User(name="System Admin", email="admin@internhub.com", role="admin")
    admin.set_password("admin123")
    db.session.add(admin)

    mentor_user = User(name="Priya Sharma", email="mentor@internhub.com", role="mentor")
    mentor_user.set_password("mentor123")
    db.session.add(mentor_user)
    db.session.flush()

    mentor = Mentor(
        user_id=mentor_user.id,
        department="Engineering",
        designation="Senior Software Engineer",
        experience=6,
        phone="9876543210",
    )
    db.session.add(mentor)
    db.session.flush()

    intern_user = User(name="Rahul Verma", email="intern@internhub.com", role="intern")
    intern_user.set_password("intern123")
    db.session.add(intern_user)
    db.session.flush()

    from datetime import date, timedelta

    today = date.today()
    intern = Intern(
        user_id=intern_user.id,
        college="National Institute of Technology",
        branch="Computer Science",
        year=3,
        phone="9123456780",
        address="Bengaluru, Karnataka",
        joining_date=today - timedelta(days=45),
        ending_date=today + timedelta(days=75),
        mentor_id=mentor.id,
        status="active",
        github="https://github.com/rahulverma",
        linkedin="https://linkedin.com/in/rahulverma",
    )
    db.session.add(intern)

    mentor2_user = User(name="Amit Patel", email="amit.mentor@internhub.com", role="mentor")
    mentor2_user.set_password("mentor123")
    db.session.add(mentor2_user)
    db.session.flush()
    mentor2 = Mentor(
        user_id=mentor2_user.id,
        department="Data Science",
        designation="Tech Lead",
        experience=8,
        phone="9988776655",
    )
    db.session.add(mentor2)
    db.session.flush()

    sample_branches = [
        ("Computer Science", "IIT Delhi"),
        ("Information Technology", "VIT Vellore"),
        ("Electronics", "BITS Pilani"),
        ("Computer Science", "IIIT Hyderabad"),
        ("Mechanical", "NIT Trichy"),
    ]
    for idx, (branch, college) in enumerate(sample_branches, start=1):
        u = User(
            name=f"Intern {idx}",
            email=f"intern{idx}@internhub.com",
            role="intern",
        )
        u.set_password("intern123")
        db.session.add(u)
        db.session.flush()
        db.session.add(
            Intern(
                user_id=u.id,
                college=college,
                branch=branch,
                year=(idx % 4) + 1,
                phone=f"900000000{idx}",
                address=f"City {idx}, India",
                joining_date=today - timedelta(days=30 * idx),
                ending_date=today + timedelta(days=60),
                mentor_id=mentor.id if idx % 2 else mentor2.id,
                status="active" if idx < 5 else "completed",
                github=f"https://github.com/intern{idx}",
            )
        )

    project = Project(
        title="InternHub Portal Enhancement",
        description="Build dashboards, attendance tracking, and reporting modules for the internship portal.",
        technology="Flask, SQLAlchemy, Bootstrap, Chart.js",
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=60),
        mentor_id=mentor.id,
    )
    db.session.add(project)
    db.session.flush()

    from models import Assignment, Task

    db.session.add(
        Assignment(intern_id=intern.id, project_id=project.id, status="in_progress")
    )
    db.session.add(
        Task(
            mentor_id=mentor.id,
            intern_id=intern.id,
            title="Setup Project Repository",
            description="Initialize GitHub repository with README and basic Flask structure.",
            deadline=today + timedelta(days=3),
            status="pending",
        )
    )

    for i in range(7):
        d = today - timedelta(days=i)
        status = "Present" if i % 3 else ("Leave" if i == 4 else "Present")
        if i == 2:
            status = "Absent"
        db.session.add(
            Attendance(
                intern_id=intern.id,
                date=d,
                check_in="09:30" if status == "Present" else None,
                check_out="18:00" if status == "Present" else None,
                status=status,
            )
        )

    db.session.add(
        Feedback(
            mentor_id=mentor.id,
            intern_id=intern.id,
            rating=4,
            comments="Strong learning attitude and consistent delivery. Keep improving code reviews.",
            date=today,
        )
    )

    db.session.commit()


def export_csv(rows, headers, filename_prefix):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    content = output.getvalue()
    output.close()
    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return content, filename


def build_pdf_table(title, headers, rows):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.6 * inch, rightMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(title, styles["Title"]),
        Paragraph(f"Generated on {datetime.now().strftime('%d %b %Y %H:%M')}", styles["Normal"]),
        Spacer(1, 0.25 * inch),
    ]

    data = [headers] + rows
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e5aaf")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.Color(0.93, 0.95, 0.98)]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    filename = f"{title.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return buffer, filename
