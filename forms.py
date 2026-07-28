from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    DateField,
    EmailField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    Regexp,
    URL,
    ValidationError,
)

from models import User


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class MentorForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=120)])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[Optional(), Length(min=6, max=64)])
    department = StringField("Department", validators=[DataRequired(), Length(max=120)])
    designation = StringField("Designation", validators=[DataRequired(), Length(max=120)])
    experience = IntegerField("Experience (Years)", validators=[DataRequired(), NumberRange(min=0, max=50)])
    phone = StringField(
        "Phone",
        validators=[
            DataRequired(),
            Regexp(r"^[0-9+\-\s]{7,20}$", message="Enter a valid phone number"),
        ],
    )
    profile_image = FileField(
        "Profile Image",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "gif", "webp"], "Images only!")],
    )
    submit = SubmitField("Save Mentor")

    def __init__(self, original_email=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, field):
        if self.original_email and field.data == self.original_email:
            return
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("Email is already registered.")


class InternForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=120)])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[Optional(), Length(min=6, max=64)])
    college = StringField("College", validators=[DataRequired(), Length(max=200)])
    branch = StringField("Branch", validators=[DataRequired(), Length(max=120)])
    year = IntegerField("Year", validators=[DataRequired(), NumberRange(min=1, max=6)])
    phone = StringField(
        "Phone",
        validators=[
            DataRequired(),
            Regexp(r"^[0-9+\-\s]{7,20}$", message="Enter a valid phone number"),
        ],
    )
    address = StringField("Address", validators=[DataRequired(), Length(max=255)])
    joining_date = DateField("Joining Date", validators=[DataRequired()])
    ending_date = DateField("Ending Date", validators=[Optional()])
    mentor_id = SelectField("Mentor", coerce=int, validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("active", "Active"), ("completed", "Completed"), ("inactive", "Inactive")],
        validators=[DataRequired()],
    )
    github = StringField("GitHub URL", validators=[Optional(), URL(), Length(max=255)])
    linkedin = StringField("LinkedIn URL", validators=[Optional(), URL(), Length(max=255)])
    resume = FileField(
        "Resume",
        validators=[Optional(), FileAllowed(["pdf", "doc", "docx"], "PDF/DOC/DOCX only!")],
    )
    profile_image = FileField(
        "Profile Image",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "gif", "webp"], "Images only!")],
    )
    submit = SubmitField("Save Intern")

    def __init__(self, original_email=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, field):
        if self.original_email and field.data == self.original_email:
            return
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("Email is already registered.")


class ProjectForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description", validators=[DataRequired(), Length(min=10)])
    technology = StringField("Technology", validators=[DataRequired(), Length(max=200)])
    start_date = DateField("Start Date", validators=[DataRequired()])
    end_date = DateField("End Date", validators=[Optional()])
    mentor_id = SelectField("Mentor", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Save Project")


class AssignmentForm(FlaskForm):
    intern_id = SelectField("Intern", coerce=int, validators=[DataRequired()])
    project_id = SelectField("Project", coerce=int, validators=[DataRequired()])
    status = SelectField(
        "Status",
        choices=[
            ("assigned", "Assigned"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Assign Project")


class AttendanceForm(FlaskForm):
    intern_id = SelectField("Intern", coerce=int, validators=[DataRequired()])
    date = DateField("Date", validators=[DataRequired()])
    check_in = TimeField("Check In", validators=[Optional()], format="%H:%M")
    check_out = TimeField("Check Out", validators=[Optional()], format="%H:%M")
    status = SelectField(
        "Status",
        choices=[("Present", "Present"), ("Absent", "Absent"), ("Leave", "Leave")],
        validators=[DataRequired()],
    )
    submit = SubmitField("Save Attendance")


class TaskForm(FlaskForm):
    intern_id = SelectField("Intern", coerce=int, validators=[DataRequired()])
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description", validators=[DataRequired(), Length(min=5)])
    deadline = DateField("Deadline", validators=[DataRequired()])
    status = SelectField(
        "Status",
        choices=[
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Save Task")


class SubmissionForm(FlaskForm):
    github_link = StringField("GitHub Repository Link", validators=[DataRequired(), URL(), Length(max=255)])
    remarks = TextAreaField("Remarks", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Submit Task")


class FeedbackForm(FlaskForm):
    intern_id = SelectField("Intern", coerce=int, validators=[DataRequired()])
    rating = SelectField(
        "Rating",
        choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")],
        coerce=int,
        validators=[DataRequired()],
    )
    comments = TextAreaField("Comments", validators=[DataRequired(), Length(min=5, max=1000)])
    submit = SubmitField("Submit Feedback")


class CertificateForm(FlaskForm):
    intern_id = SelectField("Intern", coerce=int, validators=[DataRequired()])
    certificate_file = FileField(
        "Certificate File",
        validators=[
            DataRequired(),
            FileAllowed(["pdf", "png", "jpg", "jpeg"], "PDF or image only!"),
        ],
    )
    issue_date = DateField("Issue Date", validators=[DataRequired()])
    submit = SubmitField("Generate Certificate")


class ProfileForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=120)])
    phone = StringField(
        "Phone",
        validators=[
            DataRequired(),
            Regexp(r"^[0-9+\-\s]{7,20}$", message="Enter a valid phone number"),
        ],
    )
    address = StringField("Address", validators=[Optional(), Length(max=255)])
    github = StringField("GitHub URL", validators=[Optional(), URL(), Length(max=255)])
    linkedin = StringField("LinkedIn URL", validators=[Optional(), URL(), Length(max=255)])
    profile_image = FileField(
        "Profile Image",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "gif", "webp"], "Images only!")],
    )
    resume = FileField(
        "Resume",
        validators=[Optional(), FileAllowed(["pdf", "doc", "docx"], "PDF/DOC/DOCX only!")],
    )
    password = PasswordField("New Password", validators=[Optional(), Length(min=6, max=64)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[Optional(), EqualTo("password", message="Passwords must match")],
    )
    submit = SubmitField("Update Profile")


class SearchForm(FlaskForm):
    q = StringField("Search", validators=[Optional(), Length(max=120)])
    submit = SubmitField("Search")


class OfficeLocationForm(FlaskForm):
    name = StringField("Location Name", validators=[DataRequired(), Length(max=120)])
    latitude = StringField("Latitude", validators=[DataRequired()])
    longitude = StringField("Longitude", validators=[DataRequired()])
    radius_meters = IntegerField("Radius (meters)", validators=[DataRequired(), NumberRange(min=10, max=1000)])
    is_active = SelectField("Active", choices=[(True, "Yes"), (False, "No")], coerce=bool)
    submit = SubmitField("Save Location")


class InternTimingForm(FlaskForm):
    intern_id = SelectField("Intern", coerce=int, validators=[DataRequired()])
    timing_type = SelectField(
        "Timing Type",
        choices=[("fixed", "Fixed Timing"), ("flexible", "Flexible Timing")],
        validators=[DataRequired()],
    )
    start_time = StringField("Start Time (HH:MM)", validators=[Optional(), Regexp(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", message="Use HH:MM format")])
    end_time = StringField("End Time (HH:MM)", validators=[Optional(), Regexp(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", message="Use HH:MM format")])
    required_hours = IntegerField("Required Hours (for flexible)", validators=[Optional(), NumberRange(min=1, max=24)])
    grace_minutes = IntegerField("Grace Minutes", validators=[DataRequired(), NumberRange(min=0, max=60)])
    submit = SubmitField("Save Timing Settings")


class CheckInForm(FlaskForm):
    latitude = StringField("Latitude", validators=[DataRequired()])
    longitude = StringField("Longitude", validators=[DataRequired()])
    submit = SubmitField("Check In")


class CheckOutForm(FlaskForm):
    latitude = StringField("Latitude", validators=[DataRequired()])
    longitude = StringField("Longitude", validators=[DataRequired()])
    submit = SubmitField("Check Out")
