import calendar
from datetime import date, datetime

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import login_required
from sqlalchemy import extract, func

from extensions import db
from forms import (
    AssignmentForm,
    AttendanceForm,
    CertificateForm,
    InternForm,
    InternTimingForm,
    MentorForm,
    OfficeLocationForm,
    ProjectForm,
)
from models import (
    Assignment,
    Attendance,
    Certificate,
    Feedback,
    Intern,
    InternTiming,
    Mentor,
    OfficeLocation,
    Project,
    Task,
    User,
)
from utils import (
    attendance_percentage,
    build_pdf_table,
    export_csv,
    format_work_hours,
    get_trusted_date,
    get_intern_choices,
    get_mentor_choices,
    get_project_choices,
    role_required,
    save_upload,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _paginate(query, page):
    return query.paginate(
        page=page,
        per_page=current_app.config["ITEMS_PER_PAGE"],
        error_out=False,
    )


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    total_interns = Intern.query.count()
    active_interns = Intern.query.filter_by(status="active").count()
    completed_interns = Intern.query.filter_by(status="completed").count()
    total_mentors = Mentor.query.count()
    total_projects = Project.query.count()
    pending_tasks = Task.query.filter(Task.status.in_(["pending", "in_progress", "submitted"])).count()
    att_pct = attendance_percentage()

    branch_rows = (
        db.session.query(Intern.branch, func.count(Intern.id))
        .group_by(Intern.branch)
        .all()
    )
    branch_labels = [r[0] for r in branch_rows] or ["No Data"]
    branch_values = [r[1] for r in branch_rows] or [0]

    month_labels = []
    month_values = []
    today = date.today()
    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        count = (
            Intern.query.filter(
                extract("year", Intern.joining_date) == year,
                extract("month", Intern.joining_date) == month,
            ).count()
        )
        month_labels.append(f"{calendar.month_abbr[month]} {year}")
        month_values.append(count)

    att_status_rows = (
        db.session.query(Attendance.status, func.count(Attendance.id))
        .group_by(Attendance.status)
        .all()
    )
    att_labels = [r[0] for r in att_status_rows] or ["Present", "Absent", "Leave"]
    att_values = [r[1] for r in att_status_rows] or [0, 0, 0]

    tech_rows = (
        db.session.query(Project.technology, func.count(Project.id))
        .group_by(Project.technology)
        .all()
    )
    tech_labels = [r[0] for r in tech_rows] or ["No Projects"]
    tech_values = [r[1] for r in tech_rows] or [0]

    task_rows = (
        db.session.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
    )
    task_labels = [r[0].replace("_", " ").title() for r in task_rows] or ["Pending"]
    task_values = [r[1] for r in task_rows] or [0]

    return render_template(
        "admin/dashboard.html",
        total_interns=total_interns,
        active_interns=active_interns,
        completed_interns=completed_interns,
        total_mentors=total_mentors,
        total_projects=total_projects,
        pending_tasks=pending_tasks,
        attendance_pct=att_pct,
        branch_labels=branch_labels,
        branch_values=branch_values,
        month_labels=month_labels,
        month_values=month_values,
        att_labels=att_labels,
        att_values=att_values,
        tech_labels=tech_labels,
        tech_values=tech_values,
        task_labels=task_labels,
        task_values=task_values,
    )


# -------------------- Mentors --------------------
@admin_bp.route("/mentors")
@login_required
@role_required("admin")
def mentors():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    department = request.args.get("department", "").strip()

    query = Mentor.query.join(User)
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(User.name.ilike(like), User.email.ilike(like), Mentor.phone.ilike(like))
        )
    if department:
        query = query.filter(Mentor.department.ilike(f"%{department}%"))

    pagination = _paginate(query.order_by(User.name), page)
    return render_template(
        "admin/mentors.html",
        mentors=pagination.items,
        pagination=pagination,
        q=q,
        department=department,
    )


@admin_bp.route("/mentors/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_mentor():
    form = MentorForm()
    if form.validate_on_submit():
        if not form.password.data:
            form.password.errors.append("Password is required for new mentors.")
            return render_template("admin/mentor_form.html", form=form, title="Add Mentor")

        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            role="mentor",
        )
        user.set_password(form.password.data)
        if form.profile_image.data:
            user.profile_image = save_upload(
                form.profile_image.data,
                "profiles",
                current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
            )
        db.session.add(user)
        db.session.flush()
        mentor = Mentor(
            user_id=user.id,
            department=form.department.data.strip(),
            designation=form.designation.data.strip(),
            experience=form.experience.data,
            phone=form.phone.data.strip(),
        )
        db.session.add(mentor)
        db.session.commit()
        flash("Mentor added successfully.", "success")
        return redirect(url_for("admin.mentors"))
    return render_template("admin/mentor_form.html", form=form, title="Add Mentor")


@admin_bp.route("/mentors/<int:mentor_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_mentor(mentor_id):
    mentor = Mentor.query.get_or_404(mentor_id)
    form = MentorForm(original_email=mentor.user.email, obj=mentor)
    if request.method == "GET":
        form.name.data = mentor.user.name
        form.email.data = mentor.user.email

    if form.validate_on_submit():
        mentor.user.name = form.name.data.strip()
        mentor.user.email = form.email.data.lower().strip()
        if form.password.data:
            mentor.user.set_password(form.password.data)
        if form.profile_image.data:
            mentor.user.profile_image = save_upload(
                form.profile_image.data,
                "profiles",
                current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
            )
        mentor.department = form.department.data.strip()
        mentor.designation = form.designation.data.strip()
        mentor.experience = form.experience.data
        mentor.phone = form.phone.data.strip()
        db.session.commit()
        flash("Mentor updated successfully.", "success")
        return redirect(url_for("admin.mentors"))
    return render_template("admin/mentor_form.html", form=form, title="Edit Mentor")


@admin_bp.route("/mentors/<int:mentor_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_mentor(mentor_id):
    mentor = Mentor.query.get_or_404(mentor_id)
    if mentor.projects.count() or mentor.tasks.count() or mentor.feedbacks.count():
        flash(
            "Cannot delete mentor with existing projects, tasks, or feedback. Reassign or remove those first.",
            "warning",
        )
        return redirect(url_for("admin.mentors"))
    user = mentor.user
    Intern.query.filter_by(mentor_id=mentor.id).update({"mentor_id": None})
    db.session.delete(mentor)
    db.session.delete(user)
    db.session.commit()
    flash("Mentor deleted successfully.", "success")
    return redirect(url_for("admin.mentors"))


# -------------------- Interns --------------------
@admin_bp.route("/interns")
@login_required
@role_required("admin")
def interns():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    branch = request.args.get("branch", "").strip()

    query = Intern.query.join(User)
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                User.name.ilike(like),
                User.email.ilike(like),
                Intern.college.ilike(like),
                Intern.phone.ilike(like),
            )
        )
    if status:
        query = query.filter(Intern.status == status)
    if branch:
        query = query.filter(Intern.branch.ilike(f"%{branch}%"))

    pagination = _paginate(query.order_by(User.name), page)
    return render_template(
        "admin/interns.html",
        interns=pagination.items,
        pagination=pagination,
        q=q,
        status=status,
        branch=branch,
    )


@admin_bp.route("/interns/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_intern():
    form = InternForm()
    form.mentor_id.choices = get_mentor_choices()
    if form.validate_on_submit():
        if not form.password.data:
            form.password.errors.append("Password is required for new interns.")
            return render_template("admin/intern_form.html", form=form, title="Add Intern")

        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            role="intern",
        )
        user.set_password(form.password.data)
        if form.profile_image.data:
            user.profile_image = save_upload(
                form.profile_image.data,
                "profiles",
                current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
            )
        db.session.add(user)
        db.session.flush()

        resume_path = None
        if form.resume.data:
            resume_path = save_upload(
                form.resume.data,
                "resumes",
                current_app.config["ALLOWED_DOCUMENT_EXTENSIONS"],
            )

        intern = Intern(
            user_id=user.id,
            college=form.college.data.strip(),
            branch=form.branch.data.strip(),
            year=form.year.data,
            phone=form.phone.data.strip(),
            address=form.address.data.strip(),
            joining_date=form.joining_date.data,
            ending_date=form.ending_date.data,
            mentor_id=form.mentor_id.data or None,
            status=form.status.data,
            github=form.github.data or None,
            linkedin=form.linkedin.data or None,
            resume=resume_path,
        )
        db.session.add(intern)
        db.session.commit()
        flash("Intern added successfully.", "success")
        return redirect(url_for("admin.interns"))
    return render_template("admin/intern_form.html", form=form, title="Add Intern")


@admin_bp.route("/interns/<int:intern_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_intern(intern_id):
    intern = Intern.query.get_or_404(intern_id)
    form = InternForm(original_email=intern.user.email)
    form.mentor_id.choices = get_mentor_choices()
    if request.method == "GET":
        form.name.data = intern.user.name
        form.email.data = intern.user.email
        form.college.data = intern.college
        form.branch.data = intern.branch
        form.year.data = intern.year
        form.phone.data = intern.phone
        form.address.data = intern.address
        form.joining_date.data = intern.joining_date
        form.ending_date.data = intern.ending_date
        form.mentor_id.data = intern.mentor_id or 0
        form.status.data = intern.status
        form.github.data = intern.github
        form.linkedin.data = intern.linkedin

    if form.validate_on_submit():
        intern.user.name = form.name.data.strip()
        intern.user.email = form.email.data.lower().strip()
        if form.password.data:
            intern.user.set_password(form.password.data)
        if form.profile_image.data:
            intern.user.profile_image = save_upload(
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
        intern.college = form.college.data.strip()
        intern.branch = form.branch.data.strip()
        intern.year = form.year.data
        intern.phone = form.phone.data.strip()
        intern.address = form.address.data.strip()
        intern.joining_date = form.joining_date.data
        intern.ending_date = form.ending_date.data
        intern.mentor_id = form.mentor_id.data or None
        intern.status = form.status.data
        intern.github = form.github.data or None
        intern.linkedin = form.linkedin.data or None
        db.session.commit()
        flash("Intern updated successfully.", "success")
        return redirect(url_for("admin.interns"))
    return render_template("admin/intern_form.html", form=form, title="Edit Intern")


@admin_bp.route("/interns/<int:intern_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_intern(intern_id):
    intern = Intern.query.get_or_404(intern_id)
    user = intern.user
    db.session.delete(intern)
    db.session.delete(user)
    db.session.commit()
    flash("Intern deleted successfully.", "success")
    return redirect(url_for("admin.interns"))


# -------------------- Projects --------------------
@admin_bp.route("/projects")
@login_required
@role_required("admin")
def projects():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    query = Project.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Project.title.ilike(like),
                Project.technology.ilike(like),
                Project.description.ilike(like),
            )
        )
    pagination = _paginate(query.order_by(Project.start_date.desc()), page)
    return render_template(
        "admin/projects.html",
        projects=pagination.items,
        pagination=pagination,
        q=q,
    )


@admin_bp.route("/projects/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_project():
    form = ProjectForm()
    form.mentor_id.choices = [
        (m_id, name) for m_id, name in get_mentor_choices() if m_id != 0
    ]
    if not form.mentor_id.choices:
        form.mentor_id.choices = [(0, "No mentors available")]
    if form.validate_on_submit():
        project = Project(
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            technology=form.technology.data.strip(),
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            mentor_id=form.mentor_id.data,
        )
        db.session.add(project)
        db.session.commit()
        flash("Project created successfully.", "success")
        return redirect(url_for("admin.projects"))
    return render_template("admin/project_form.html", form=form, title="Create Project")


@admin_bp.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    form = ProjectForm(obj=project)
    form.mentor_id.choices = [(m_id, name) for m_id, name in get_mentor_choices() if m_id != 0]
    if request.method == "GET":
        form.mentor_id.data = project.mentor_id
    if form.validate_on_submit():
        project.title = form.title.data.strip()
        project.description = form.description.data.strip()
        project.technology = form.technology.data.strip()
        project.start_date = form.start_date.data
        project.end_date = form.end_date.data
        project.mentor_id = form.mentor_id.data
        db.session.commit()
        flash("Project updated successfully.", "success")
        return redirect(url_for("admin.projects"))
    return render_template("admin/project_form.html", form=form, title="Edit Project")


@admin_bp.route("/assignments", methods=["GET", "POST"])
@login_required
@role_required("admin")
def assignments():
    form = AssignmentForm()
    form.intern_id.choices = get_intern_choices()
    form.project_id.choices = get_project_choices()
    page = request.args.get("page", 1, type=int)

    if form.validate_on_submit():
        existing = Assignment.query.filter_by(
            intern_id=form.intern_id.data, project_id=form.project_id.data
        ).first()
        if existing:
            existing.status = form.status.data
            flash("Assignment updated.", "info")
        else:
            db.session.add(
                Assignment(
                    intern_id=form.intern_id.data,
                    project_id=form.project_id.data,
                    status=form.status.data,
                )
            )
            flash("Project assigned successfully.", "success")
        db.session.commit()
        return redirect(url_for("admin.assignments"))

    pagination = _paginate(Assignment.query.order_by(Assignment.assigned_date.desc()), page)
    return render_template(
        "admin/assignments.html",
        form=form,
        assignments=pagination.items,
        pagination=pagination,
    )


# -------------------- Attendance --------------------
@admin_bp.route("/attendance", methods=["GET", "POST"])
@login_required
@role_required("admin")
def attendance():
    form = AttendanceForm()
    form.intern_id.choices = get_intern_choices()
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status", "").strip()
    q = request.args.get("q", "").strip()
    intern_id = request.args.get("intern_id", type=int)
    from_date_raw = request.args.get("from_date", "").strip()
    to_date_raw = request.args.get("to_date", "").strip()
    if not any([status, q, intern_id, from_date_raw, to_date_raw]):
        today_str = get_trusted_date().isoformat()
        from_date_raw = today_str
        to_date_raw = today_str

    if form.validate_on_submit():
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
        return redirect(url_for("admin.attendance"))

    query = Attendance.query.join(Intern).join(User)
    if status:
        query = query.filter(Attendance.status == status)
    if q:
        query = query.filter(User.name.ilike(f"%{q}%"))
    if intern_id:
        query = query.filter(Attendance.intern_id == intern_id)

    from_date = None
    if from_date_raw:
        try:
            from_date = datetime.strptime(from_date_raw, "%Y-%m-%d").date()
            query = query.filter(Attendance.date >= from_date)
        except ValueError:
            flash("Invalid from date filter ignored.", "warning")
            from_date_raw = ""

    to_date = None
    if to_date_raw:
        try:
            to_date = datetime.strptime(to_date_raw, "%Y-%m-%d").date()
            query = query.filter(Attendance.date <= to_date)
        except ValueError:
            flash("Invalid to date filter ignored.", "warning")
            to_date_raw = ""

    filtered_records = query.all()
    total_records = len(filtered_records)
    present_count = sum(1 for record in filtered_records if record.status == "Present")
    absent_count = sum(1 for record in filtered_records if record.status == "Absent")
    leave_count = sum(1 for record in filtered_records if record.status == "Leave")
    completed_hours = [record.work_hours for record in filtered_records if record.work_hours]
    avg_work_hours = format_work_hours(sum(completed_hours) / len(completed_hours)) if completed_hours else "-"

    pagination = _paginate(query.order_by(Attendance.date.desc(), User.name.asc()), page)
    return render_template(
        "admin/attendance.html",
        form=form,
        records=pagination.items,
        pagination=pagination,
        status=status,
        q=q,
        intern_id=intern_id,
        from_date=from_date_raw,
        to_date=to_date_raw,
        total_records=total_records,
        present_count=present_count,
        absent_count=absent_count,
        leave_count=leave_count,
        avg_work_hours=avg_work_hours,
    )


# -------------------- Feedback / Certificates --------------------
@admin_bp.route("/feedback")
@login_required
@role_required("admin")
def feedback():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    query = Feedback.query.join(Intern).join(User)
    if q:
        query = query.filter(User.name.ilike(f"%{q}%"))
    pagination = _paginate(query.order_by(Feedback.date.desc()), page)
    return render_template(
        "admin/feedback.html",
        feedbacks=pagination.items,
        pagination=pagination,
        q=q,
    )


@admin_bp.route("/certificates", methods=["GET", "POST"])
@login_required
@role_required("admin")
def certificates():
    form = CertificateForm()
    form.intern_id.choices = get_intern_choices()
    page = request.args.get("page", 1, type=int)

    if form.validate_on_submit():
        filepath = save_upload(
            form.certificate_file.data,
            "certificates",
            current_app.config["ALLOWED_CERTIFICATE_EXTENSIONS"],
        )
        cert = Certificate(
            intern_id=form.intern_id.data,
            certificate_file=filepath,
            issue_date=form.issue_date.data,
        )
        intern = Intern.query.get(form.intern_id.data)
        if intern:
            intern.status = "completed"
        db.session.add(cert)
        db.session.commit()
        flash("Certificate generated successfully.", "success")
        return redirect(url_for("admin.certificates"))

    pagination = _paginate(Certificate.query.order_by(Certificate.issue_date.desc()), page)
    return render_template(
        "admin/certificates.html",
        form=form,
        certificates=pagination.items,
        pagination=pagination,
    )


# -------------------- Reports --------------------
@admin_bp.route("/reports")
@login_required
@role_required("admin")
def reports():
    return render_template("admin/reports.html")


@admin_bp.route("/reports/interns.csv")
@login_required
@role_required("admin")
def export_interns_csv():
    rows = []
    for i in Intern.query.join(User).order_by(User.name).all():
        rows.append(
            [
                i.user.name,
                i.user.email,
                i.college,
                i.branch,
                i.year,
                i.phone,
                i.status,
                i.mentor.user.name if i.mentor else "",
                i.joining_date.isoformat() if i.joining_date else "",
            ]
        )
    content, filename = export_csv(
        rows,
        ["Name", "Email", "College", "Branch", "Year", "Phone", "Status", "Mentor", "Joining Date"],
        "intern_list",
    )
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_bp.route("/reports/attendance.csv")
@login_required
@role_required("admin")
def export_attendance_csv():
    rows = []
    for a in Attendance.query.join(Intern).join(User).order_by(Attendance.date.desc()).all():
        rows.append(
            [
                a.intern.user.name,
                a.date.isoformat(),
                a.check_in or "",
                a.check_out or "",
                a.work_hours_display if a.work_hours_display != "-" else "",
                a.status,
            ]
        )
    content, filename = export_csv(
        rows,
        ["Intern", "Date", "Check In", "Check Out", "Working Hours", "Status"],
        "attendance_report",
    )
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_bp.route("/reports/projects.csv")
@login_required
@role_required("admin")
def export_projects_csv():
    rows = []
    for p in Project.query.order_by(Project.title).all():
        rows.append(
            [
                p.title,
                p.technology,
                p.mentor.user.name if p.mentor else "",
                p.start_date.isoformat() if p.start_date else "",
                p.end_date.isoformat() if p.end_date else "",
                p.assignments.count(),
            ]
        )
    content, filename = export_csv(
        rows,
        ["Title", "Technology", "Mentor", "Start Date", "End Date", "Assigned Interns"],
        "project_report",
    )
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_bp.route("/reports/performance.csv")
@login_required
@role_required("admin")
def export_performance_csv():
    rows = []
    for i in Intern.query.join(User).order_by(User.name).all():
        avg_rating = (
            db.session.query(func.avg(Feedback.rating))
            .filter(Feedback.intern_id == i.id)
            .scalar()
        )
        approved = Task.query.filter_by(intern_id=i.id, status="approved").count()
        total_tasks = Task.query.filter_by(intern_id=i.id).count()
        rows.append(
            [
                i.user.name,
                i.branch,
                i.status,
                round(avg_rating or 0, 2),
                approved,
                total_tasks,
                attendance_percentage(i.id),
            ]
        )
    content, filename = export_csv(
        rows,
        ["Intern", "Branch", "Status", "Avg Rating", "Approved Tasks", "Total Tasks", "Attendance %"],
        "performance_report",
    )
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_bp.route("/reports/interns.pdf")
@login_required
@role_required("admin")
def export_interns_pdf():
    rows = []
    for i in Intern.query.join(User).order_by(User.name).all():
        rows.append(
            [
                i.user.name,
                i.branch,
                i.status,
                i.mentor.user.name if i.mentor else "-",
                i.joining_date.strftime("%d-%m-%Y") if i.joining_date else "-",
            ]
        )
    buffer, filename = build_pdf_table(
        "Intern List Report",
        ["Name", "Branch", "Status", "Mentor", "Joining"],
        rows,
    )
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")


@admin_bp.route("/reports/attendance.pdf")
@login_required
@role_required("admin")
def export_attendance_pdf():
    rows = []
    for a in Attendance.query.join(Intern).join(User).order_by(Attendance.date.desc()).limit(100).all():
        rows.append(
            [
                a.intern.user.name,
                a.date.strftime("%d-%m-%Y"),
                a.check_in or "-",
                a.check_out or "-",
                a.work_hours_display,
                a.status,
            ]
        )
    buffer, filename = build_pdf_table(
        "Attendance Report",
        ["Intern", "Date", "In", "Out", "Working Hours", "Status"],
        rows,
    )
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")


@admin_bp.route("/reports/performance.pdf")
@login_required
@role_required("admin")
def export_performance_pdf():
    rows = []
    for i in Intern.query.join(User).order_by(User.name).all():
        avg_rating = (
            db.session.query(func.avg(Feedback.rating))
            .filter(Feedback.intern_id == i.id)
            .scalar()
        )
        rows.append(
            [
                i.user.name,
                i.branch,
                str(round(avg_rating or 0, 2)),
                str(attendance_percentage(i.id)),
                i.status,
            ]
        )
    buffer, filename = build_pdf_table(
        "Performance Report",
        ["Intern", "Branch", "Rating", "Attendance %", "Status"],
        rows,
    )
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")


@admin_bp.route("/tasks")
@login_required
@role_required("admin")
def tasks():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    query = Task.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Task.title.ilike(like), Task.description.ilike(like)))
    if status:
        query = query.filter(Task.status == status)
    pagination = _paginate(query.order_by(Task.deadline.desc()), page)
    return render_template(
        "admin/tasks.html",
        tasks=pagination.items,
        pagination=pagination,
        q=q,
        status=status,
    )


# -------------------- Office Locations --------------------


@admin_bp.route("/office-locations")
@login_required
@role_required("admin")
def office_locations():
    locations = OfficeLocation.query.order_by(OfficeLocation.created_at.desc()).all()
    return render_template("admin/office_locations.html", locations=locations)


@admin_bp.route("/office-locations/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_office_location():
    form = OfficeLocationForm()
    if form.validate_on_submit():
        location = OfficeLocation(
            name=form.name.data.strip(),
            latitude=float(form.latitude.data),
            longitude=float(form.longitude.data),
            radius_meters=form.radius_meters.data,
            is_active=form.is_active.data,
        )
        db.session.add(location)
        db.session.commit()
        flash("Office location added successfully.", "success")
        return redirect(url_for("admin.office_locations"))
    return render_template("admin/office_location_form.html", form=form, title="Add Office Location")


@admin_bp.route("/office-locations/<int:location_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_office_location(location_id):
    location = OfficeLocation.query.get_or_404(location_id)
    form = OfficeLocationForm(obj=location)
    if request.method == "GET":
        form.latitude.data = str(location.latitude)
        form.longitude.data = str(location.longitude)
    if form.validate_on_submit():
        location.name = form.name.data.strip()
        location.latitude = float(form.latitude.data)
        location.longitude = float(form.longitude.data)
        location.radius_meters = form.radius_meters.data
        location.is_active = form.is_active.data
        db.session.commit()
        flash("Office location updated successfully.", "success")
        return redirect(url_for("admin.office_locations"))
    return render_template("admin/office_location_form.html", form=form, title="Edit Office Location")


@admin_bp.route("/office-locations/<int:location_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_office_location(location_id):
    location = OfficeLocation.query.get_or_404(location_id)
    db.session.delete(location)
    db.session.commit()
    flash("Office location deleted successfully.", "success")
    return redirect(url_for("admin.office_locations"))


@admin_bp.route("/office-locations/<int:location_id>/toggle", methods=["POST"])
@login_required
@role_required("admin")
def toggle_office_location(location_id):
    location = OfficeLocation.query.get_or_404(location_id)
    location.is_active = not location.is_active
    db.session.commit()
    status = "activated" if location.is_active else "deactivated"
    flash(f"Office location {status} successfully.", "success")
    return redirect(url_for("admin.office_locations"))


# -------------------- Intern Timings --------------------


@admin_bp.route("/intern-timings")
@login_required
@role_required("admin")
def intern_timings():
    page = request.args.get("page", 1, type=int)
    pagination = _paginate(
        InternTiming.query.join(Intern).join(User).order_by(User.name),
        page,
    )
    return render_template(
        "admin/intern_timings.html",
        timings=pagination.items,
        pagination=pagination,
    )


@admin_bp.route("/intern-timings/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_intern_timing():
    form = InternTimingForm()
    form.intern_id.choices = get_intern_choices()
    if form.validate_on_submit():
        timing = InternTiming(
            intern_id=form.intern_id.data,
            timing_type=form.timing_type.data,
            start_time=form.start_time.data.strip() if form.start_time.data else None,
            end_time=form.end_time.data.strip() if form.end_time.data else None,
            required_hours=form.required_hours.data,
            grace_minutes=form.grace_minutes.data,
        )
        db.session.add(timing)
        db.session.commit()
        flash("Intern timing settings added successfully.", "success")
        return redirect(url_for("admin.intern_timings"))
    return render_template("admin/intern_timing_form.html", form=form, title="Add Intern Timing")


@admin_bp.route("/intern-timings/<int:timing_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_intern_timing(timing_id):
    timing = InternTiming.query.get_or_404(timing_id)
    form = InternTimingForm(obj=timing)
    form.intern_id.choices = get_intern_choices()
    if request.method == "GET":
        form.intern_id.data = timing.intern_id
    if form.validate_on_submit():
        timing.intern_id = form.intern_id.data
        timing.timing_type = form.timing_type.data
        timing.start_time = form.start_time.data.strip() if form.start_time.data else None
        timing.end_time = form.end_time.data.strip() if form.end_time.data else None
        timing.required_hours = form.required_hours.data
        timing.grace_minutes = form.grace_minutes.data
        db.session.commit()
        flash("Intern timing settings updated successfully.", "success")
        return redirect(url_for("admin.intern_timings"))
    return render_template("admin/intern_timing_form.html", form=form, title="Edit Intern Timing")


@admin_bp.route("/intern-timings/<int:timing_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_intern_timing(timing_id):
    timing = InternTiming.query.get_or_404(timing_id)
    db.session.delete(timing)
    db.session.commit()
    flash("Intern timing settings deleted successfully.", "success")
    return redirect(url_for("admin.intern_timings"))
