import os

from flask import Flask, render_template
from flask_login import current_user

from config import Config
from extensions import csrf, db, login_manager
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
    Submission,
    Task,
    User,
)
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.intern import intern_bp
from routes.mentor import mentor_bp
from utils import seed_database


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    for sub in ("profiles", "resumes", "certificates"):
        os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], sub), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(mentor_bp)
    app.register_blueprint(intern_bp)

    @app.context_processor
    def inject_globals():
        return {"current_user": current_user, "app_name": "InternHub"}

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    with app.app_context():
        db.create_all()
        seed_database()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
