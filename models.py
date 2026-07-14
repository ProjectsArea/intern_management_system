from datetime import datetime, date

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)  # admin, mentor, intern
    profile_image = db.Column(db.String(255), default="default.png")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    mentor_profile = db.relationship(
        "Mentor", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    intern_profile = db.relationship(
        "Intern", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"<User {self.email}>"


class Mentor(db.Model):
    __tablename__ = "mentors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    department = db.Column(db.String(120), nullable=False)
    designation = db.Column(db.String(120), nullable=False)
    experience = db.Column(db.Integer, default=0)
    phone = db.Column(db.String(20), nullable=False)

    user = db.relationship("User", back_populates="mentor_profile")
    interns = db.relationship("Intern", back_populates="mentor", lazy="dynamic")
    projects = db.relationship("Project", back_populates="mentor", lazy="dynamic")
    tasks = db.relationship("Task", back_populates="mentor", lazy="dynamic")
    feedbacks = db.relationship("Feedback", back_populates="mentor", lazy="dynamic")

    def __repr__(self):
        return f"<Mentor {self.user.name if self.user else self.id}>"


class Intern(db.Model):
    __tablename__ = "interns"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    college = db.Column(db.String(200), nullable=False)
    branch = db.Column(db.String(120), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    joining_date = db.Column(db.Date, nullable=False)
    ending_date = db.Column(db.Date, nullable=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey("mentors.id"), nullable=True)
    status = db.Column(db.String(20), default="active")  # active, completed, inactive
    github = db.Column(db.String(255), nullable=True)
    linkedin = db.Column(db.String(255), nullable=True)
    resume = db.Column(db.String(255), nullable=True)

    user = db.relationship("User", back_populates="intern_profile")
    mentor = db.relationship("Mentor", back_populates="interns")
    assignments = db.relationship("Assignment", back_populates="intern", lazy="dynamic")
    attendances = db.relationship("Attendance", back_populates="intern", lazy="dynamic")
    tasks = db.relationship("Task", back_populates="intern", lazy="dynamic")
    submissions = db.relationship("Submission", back_populates="intern", lazy="dynamic")
    feedbacks = db.relationship("Feedback", back_populates="intern", lazy="dynamic")
    certificates = db.relationship("Certificate", back_populates="intern", lazy="dynamic")

    def __repr__(self):
        return f"<Intern {self.user.name if self.user else self.id}>"


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    technology = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey("mentors.id"), nullable=False)

    mentor = db.relationship("Mentor", back_populates="projects")
    assignments = db.relationship("Assignment", back_populates="project", lazy="dynamic")

    def __repr__(self):
        return f"<Project {self.title}>"


class Assignment(db.Model):
    __tablename__ = "assignments"

    id = db.Column(db.Integer, primary_key=True)
    intern_id = db.Column(db.Integer, db.ForeignKey("interns.id"), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    assigned_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default="assigned")  # assigned, in_progress, completed

    intern = db.relationship("Intern", back_populates="assignments")
    project = db.relationship("Project", back_populates="assignments")

    __table_args__ = (
        db.UniqueConstraint("intern_id", "project_id", name="uq_intern_project"),
    )


class Attendance(db.Model):
    __tablename__ = "attendances"

    id = db.Column(db.Integer, primary_key=True)
    intern_id = db.Column(db.Integer, db.ForeignKey("interns.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    check_in = db.Column(db.String(10), nullable=True)
    check_out = db.Column(db.String(10), nullable=True)
    status = db.Column(db.String(20), nullable=False)  # Present, Absent, Leave

    intern = db.relationship("Intern", back_populates="attendances")

    __table_args__ = (
        db.UniqueConstraint("intern_id", "date", name="uq_intern_date"),
    )


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey("mentors.id"), nullable=False)
    intern_id = db.Column(db.Integer, db.ForeignKey("interns.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, in_progress, submitted, approved, rejected

    mentor = db.relationship("Mentor", back_populates="tasks")
    intern = db.relationship("Intern", back_populates="tasks")
    submissions = db.relationship("Submission", back_populates="task", lazy="dynamic")


class Submission(db.Model):
    __tablename__ = "submissions"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    intern_id = db.Column(db.Integer, db.ForeignKey("interns.id"), nullable=False)
    github_link = db.Column(db.String(255), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    submitted_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="submitted")  # submitted, approved, rejected

    task = db.relationship("Task", back_populates="submissions")
    intern = db.relationship("Intern", back_populates="submissions")


class Feedback(db.Model):
    __tablename__ = "feedbacks"

    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey("mentors.id"), nullable=False)
    intern_id = db.Column(db.Integer, db.ForeignKey("interns.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, default=date.today)

    mentor = db.relationship("Mentor", back_populates="feedbacks")
    intern = db.relationship("Intern", back_populates="feedbacks")


class Certificate(db.Model):
    __tablename__ = "certificates"

    id = db.Column(db.Integer, primary_key=True)
    intern_id = db.Column(db.Integer, db.ForeignKey("interns.id"), nullable=False)
    certificate_file = db.Column(db.String(255), nullable=False)
    issue_date = db.Column(db.Date, default=date.today)

    intern = db.relationship("Intern", back_populates="certificates")
