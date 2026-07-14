from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func

from extensions import db
from forms import AttendanceForm, FeedbackForm, TaskForm
from models import Attendance, Feedback, Intern, Mentor, Submission, Task, User
from utils import (
    attendance_percentage,
    get_intern_choices,
    role_required,
)

mentor_bp = Blueprint("mentor", __name__, url_prefix="/mentor")


def _current_mentor():
    return Mentor.query.filter_by(user_id=current_user.id).first_or_404()


def _paginate(query, page):
    return query.paginate(
        page=page,
        per_page=current_app.config["ITEMS_PER_PAGE"],
        error_out=False,
    )


@mentor_bp.route("/dashboard")
@login_required
@role_required("mentor")
def dashboard():
    mentor = _current_mentor()
    interns = Intern.query.filter_by(mentor_id=mentor.id).all()
    intern_ids = [i.id for i in interns]

    total_interns = len(interns)
    active_interns = sum(1 for i in interns if i.status == "active")
    total_tasks = Task.query.filter_by(mentor_id=mentor.id).count()
    pending_reviews = Task.query.filter_by(mentor_id=mentor.id, status="submitted").count()
    att_pct = attendance_percentage() if not intern_ids else _scoped_attendance(intern_ids)

    task_rows = (
        db.session.query(Task.status, func.count(Task.id))
        .filter(Task.mentor_id == mentor.id)
        .group_by(Task.status)
        .all()
    )
    task_labels = [r[0].replace("_", " ").title() for r in task_rows] or ["Pending"]
    task_values = [r[1] for r in task_rows] or [0]

    recent_tasks = (
        Task.query.filter_by(mentor_id=mentor.id)
        .order_by(Task.deadline.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "mentor/dashboard.html",
        mentor=mentor,
        total_interns=total_interns,
        active_interns=active_interns,
        total_tasks=total_tasks,
        pending_reviews=pending_reviews,
        attendance_pct=att_pct,
        task_labels=task_labels,
        task_values=task_values,
        recent_tasks=recent_tasks,
    )


def _scoped_attendance(intern_ids):
    total = Attendance.query.filter(Attendance.intern_id.in_(intern_ids)).count()
    if total == 0:
        return 0
    present = Attendance.query.filter(
        Attendance.intern_id.in_(intern_ids), Attendance.status == "Present"
    ).count()
    return round((present / total) * 100, 1)


@mentor_bp.route("/interns")
@login_required
@role_required("mentor")
def interns():
    mentor = _current_mentor()
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    query = Intern.query.join(User).filter(Intern.mentor_id == mentor.id)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.name.ilike(like), Intern.branch.ilike(like)))
    pagination = _paginate(query.order_by(User.name), page)
    return render_template(
        "mentor/interns.html",
        interns=pagination.items,
        pagination=pagination,
        q=q,
    )


@mentor_bp.route("/tasks", methods=["GET", "POST"])
@login_required
@role_required("mentor")
def tasks():
    mentor = _current_mentor()
    form = TaskForm()
    form.intern_id.choices = get_intern_choices(mentor_id=mentor.id)
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    if form.validate_on_submit():
        task = Task(
            mentor_id=mentor.id,
            intern_id=form.intern_id.data,
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            deadline=form.deadline.data,
            status=form.status.data,
        )
        db.session.add(task)
        db.session.commit()
        flash("Task created successfully.", "success")
        return redirect(url_for("mentor.tasks"))

    query = Task.query.filter_by(mentor_id=mentor.id)
    if q:
        query = query.filter(Task.title.ilike(f"%{q}%"))
    if status:
        query = query.filter(Task.status == status)
    pagination = _paginate(query.order_by(Task.deadline.desc()), page)
    return render_template(
        "mentor/tasks.html",
        form=form,
        tasks=pagination.items,
        pagination=pagination,
        q=q,
        status=status,
    )


@mentor_bp.route("/tasks/<int:task_id>/status", methods=["POST"])
@login_required
@role_required("mentor")
def update_task_status(task_id):
    mentor = _current_mentor()
    task = Task.query.filter_by(id=task_id, mentor_id=mentor.id).first_or_404()
    new_status = request.form.get("status")
    if new_status in {"pending", "in_progress", "submitted", "approved", "rejected"}:
        task.status = new_status
        latest = (
            Submission.query.filter_by(task_id=task.id)
            .order_by(Submission.submitted_date.desc())
            .first()
        )
        if latest and new_status in {"approved", "rejected"}:
            latest.status = new_status
        db.session.commit()
        flash("Task status updated.", "success")
    return redirect(request.referrer or url_for("mentor.tasks"))


@mentor_bp.route("/submissions")
@login_required
@role_required("mentor")
def submissions():
    mentor = _current_mentor()
    page = request.args.get("page", 1, type=int)
    query = (
        Submission.query.join(Task)
        .filter(Task.mentor_id == mentor.id)
        .order_by(Submission.submitted_date.desc())
    )
    pagination = _paginate(query, page)
    return render_template(
        "mentor/submissions.html",
        submissions=pagination.items,
        pagination=pagination,
    )


@mentor_bp.route("/submissions/<int:submission_id>/review", methods=["POST"])
@login_required
@role_required("mentor")
def review_submission(submission_id):
    mentor = _current_mentor()
    submission = (
        Submission.query.join(Task)
        .filter(Submission.id == submission_id, Task.mentor_id == mentor.id)
        .first_or_404()
    )
    action = request.form.get("action")
    if action in {"approved", "rejected"}:
        submission.status = action
        submission.task.status = action
        db.session.commit()
        flash(f"Submission {action}.", "success")
    return redirect(url_for("mentor.submissions"))


@mentor_bp.route("/attendance", methods=["GET", "POST"])
@login_required
@role_required("mentor")
def attendance():
    mentor = _current_mentor()
    form = AttendanceForm()
    form.intern_id.choices = get_intern_choices(mentor_id=mentor.id)
    page = request.args.get("page", 1, type=int)

    if form.validate_on_submit():
        intern = Intern.query.filter_by(id=form.intern_id.data, mentor_id=mentor.id).first()
        if not intern:
            flash("Invalid intern selection.", "danger")
            return redirect(url_for("mentor.attendance"))

        check_in = form.check_in.data.strftime("%H:%M") if form.check_in.data else None
        check_out = form.check_out.data.strftime("%H:%M") if form.check_out.data else None
        record = Attendance.query.filter_by(
            intern_id=form.intern_id.data, date=form.date.data
        ).first()
        if record:
            record.check_in = check_in
            record.check_out = check_out
            record.status = form.status.data
            flash("Attendance updated.", "info")
        else:
            db.session.add(
                Attendance(
                    intern_id=form.intern_id.data,
                    date=form.date.data,
                    check_in=check_in,
                    check_out=check_out,
                    status=form.status.data,
                )
            )
            flash("Attendance marked.", "success")
        db.session.commit()
        return redirect(url_for("mentor.attendance"))

    intern_ids = [i.id for i in Intern.query.filter_by(mentor_id=mentor.id).all()]
    query = Attendance.query.filter(Attendance.intern_id.in_(intern_ids or [-1])).order_by(
        Attendance.date.desc()
    )
    pagination = _paginate(query, page)
    return render_template(
        "mentor/attendance.html",
        form=form,
        records=pagination.items,
        pagination=pagination,
    )


@mentor_bp.route("/feedback", methods=["GET", "POST"])
@login_required
@role_required("mentor")
def feedback():
    mentor = _current_mentor()
    form = FeedbackForm()
    form.intern_id.choices = get_intern_choices(mentor_id=mentor.id)
    page = request.args.get("page", 1, type=int)

    if form.validate_on_submit():
        fb = Feedback(
            mentor_id=mentor.id,
            intern_id=form.intern_id.data,
            rating=form.rating.data,
            comments=form.comments.data.strip(),
        )
        db.session.add(fb)
        db.session.commit()
        flash("Feedback submitted successfully.", "success")
        return redirect(url_for("mentor.feedback"))

    pagination = _paginate(
        Feedback.query.filter_by(mentor_id=mentor.id).order_by(Feedback.date.desc()),
        page,
    )
    return render_template(
        "mentor/feedback.html",
        form=form,
        feedbacks=pagination.items,
        pagination=pagination,
    )
