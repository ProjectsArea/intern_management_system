from datetime import date

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func

from extensions import db
from forms import ProfileForm, SubmissionForm
from models import (
    Assignment,
    Attendance,
    Certificate,
    Feedback,
    Intern,
    Submission,
    Task,
)
from utils import attendance_percentage, role_required, save_upload

intern_bp = Blueprint("intern", __name__, url_prefix="/intern")


def _current_intern():
    return Intern.query.filter_by(user_id=current_user.id).first_or_404()


def _paginate(query, page):
    return query.paginate(
        page=page,
        per_page=current_app.config["ITEMS_PER_PAGE"],
        error_out=False,
    )


@intern_bp.route("/dashboard")
@login_required
@role_required("intern")
def dashboard():
    intern = _current_intern()
    assignment = (
        Assignment.query.filter_by(intern_id=intern.id)
        .order_by(Assignment.assigned_date.desc())
        .first()
    )
    pending_tasks = Task.query.filter(
        Task.intern_id == intern.id,
        Task.status.in_(["pending", "in_progress", "rejected"]),
    ).count()
    approved_tasks = Task.query.filter_by(intern_id=intern.id, status="approved").count()
    att_pct = attendance_percentage(intern.id)
    avg_rating = (
        db.session.query(func.avg(Feedback.rating))
        .filter(Feedback.intern_id == intern.id)
        .scalar()
    )
    recent_tasks = (
        Task.query.filter_by(intern_id=intern.id)
        .order_by(Task.deadline.asc())
        .limit(5)
        .all()
    )
    certificates = Certificate.query.filter_by(intern_id=intern.id).count()

    status_rows = (
        db.session.query(Task.status, func.count(Task.id))
        .filter(Task.intern_id == intern.id)
        .group_by(Task.status)
        .all()
    )
    task_labels = [r[0].replace("_", " ").title() for r in status_rows] or ["No Tasks"]
    task_values = [r[1] for r in status_rows] or [0]

    return render_template(
        "intern/dashboard.html",
        intern=intern,
        assignment=assignment,
        pending_tasks=pending_tasks,
        approved_tasks=approved_tasks,
        attendance_pct=att_pct,
        avg_rating=round(avg_rating or 0, 1),
        recent_tasks=recent_tasks,
        certificates=certificates,
        task_labels=task_labels,
        task_values=task_values,
    )


@intern_bp.route("/mentor")
@login_required
@role_required("intern")
def mentor():
    intern = _current_intern()
    return render_template("intern/mentor.html", intern=intern)


@intern_bp.route("/project")
@login_required
@role_required("intern")
def project():
    intern = _current_intern()
    assignments = (
        Assignment.query.filter_by(intern_id=intern.id)
        .order_by(Assignment.assigned_date.desc())
        .all()
    )
    return render_template("intern/project.html", intern=intern, assignments=assignments)


@intern_bp.route("/attendance")
@login_required
@role_required("intern")
def attendance():
    intern = _current_intern()
    page = request.args.get("page", 1, type=int)
    pagination = _paginate(
        Attendance.query.filter_by(intern_id=intern.id).order_by(Attendance.date.desc()),
        page,
    )
    return render_template(
        "intern/attendance.html",
        records=pagination.items,
        pagination=pagination,
        attendance_pct=attendance_percentage(intern.id),
    )


@intern_bp.route("/tasks")
@login_required
@role_required("intern")
def tasks():
    intern = _current_intern()
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status", "").strip()
    query = Task.query.filter_by(intern_id=intern.id)
    if status:
        query = query.filter(Task.status == status)
    pagination = _paginate(query.order_by(Task.deadline.asc()), page)
    return render_template(
        "intern/tasks.html",
        tasks=pagination.items,
        pagination=pagination,
        status=status,
    )


@intern_bp.route("/tasks/<int:task_id>/submit", methods=["GET", "POST"])
@login_required
@role_required("intern")
def submit_task(task_id):
    intern = _current_intern()
    task = Task.query.filter_by(id=task_id, intern_id=intern.id).first_or_404()
    form = SubmissionForm()

    if form.validate_on_submit():
        submission = Submission(
            task_id=task.id,
            intern_id=intern.id,
            github_link=form.github_link.data.strip(),
            remarks=form.remarks.data.strip() if form.remarks.data else None,
            status="submitted",
        )
        task.status = "submitted"
        db.session.add(submission)
        db.session.commit()
        flash("Task submitted successfully.", "success")
        return redirect(url_for("intern.tasks"))

    return render_template("intern/submit_task.html", form=form, task=task)


@intern_bp.route("/feedback")
@login_required
@role_required("intern")
def feedback():
    intern = _current_intern()
    page = request.args.get("page", 1, type=int)
    pagination = _paginate(
        Feedback.query.filter_by(intern_id=intern.id).order_by(Feedback.date.desc()),
        page,
    )
    return render_template(
        "intern/feedback.html",
        feedbacks=pagination.items,
        pagination=pagination,
    )


@intern_bp.route("/certificates")
@login_required
@role_required("intern")
def certificates():
    intern = _current_intern()
    page = request.args.get("page", 1, type=int)
    pagination = _paginate(
        Certificate.query.filter_by(intern_id=intern.id).order_by(Certificate.issue_date.desc()),
        page,
    )
    return render_template(
        "intern/certificates.html",
        certificates=pagination.items,
        pagination=pagination,
    )


@intern_bp.route("/certificates/<int:cert_id>/download")
@login_required
@role_required("intern")
def download_certificate(cert_id):
    intern = _current_intern()
    cert = Certificate.query.filter_by(id=cert_id, intern_id=intern.id).first_or_404()
    folder = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(folder, cert.certificate_file, as_attachment=True)


@intern_bp.route("/profile", methods=["GET", "POST"])
@login_required
@role_required("intern")
def profile():
    intern = _current_intern()
    form = ProfileForm()

    if request.method == "GET":
        form.name.data = current_user.name
        form.phone.data = intern.phone
        form.address.data = intern.address
        form.github.data = intern.github
        form.linkedin.data = intern.linkedin

    if form.validate_on_submit():
        current_user.name = form.name.data.strip()
        intern.phone = form.phone.data.strip()
        intern.address = form.address.data.strip() if form.address.data else intern.address
        intern.github = form.github.data or None
        intern.linkedin = form.linkedin.data or None

        if form.profile_image.data:
            current_user.profile_image = save_upload(
                form.profile_image.data,
                "profiles",
                current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
            )
        if form.resume.data:
            intern.resume = save_upload(
                form.resume.data,
                "resumes",
                current_app.config["ALLOWED_DOCUMENT_EXTENSIONS"],
            )
        if form.password.data:
            current_user.set_password(form.password.data)

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("intern.profile"))

    return render_template("intern/profile.html", form=form, intern=intern)


@intern_bp.route("/upload-certificate", methods=["POST"])
@login_required
@role_required("intern")
def upload_certificate():
    intern = _current_intern()
    file = request.files.get("certificate_file")
    if not file or not file.filename:
        flash("Please select a certificate file.", "warning")
        return redirect(url_for("intern.certificates"))

    try:
        filepath = save_upload(
            file,
            "certificates",
            current_app.config["ALLOWED_CERTIFICATE_EXTENSIONS"],
        )
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("intern.certificates"))

    db.session.add(
        Certificate(
            intern_id=intern.id,
            certificate_file=filepath,
            issue_date=date.today(),
        )
    )
    db.session.commit()
    flash("Certificate uploaded successfully.", "success")
    return redirect(url_for("intern.certificates"))
