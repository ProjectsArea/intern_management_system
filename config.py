import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "internhub-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "internhub.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    ALLOWED_DOCUMENT_EXTENSIONS = {"pdf", "doc", "docx"}
    ALLOWED_CERTIFICATE_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

    ITEMS_PER_PAGE = 10

    # Attendance uses this timezone; time is taken from a trusted external source
    # when available so client/system clock changes cannot affect check-in/out.
    APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "Asia/Kolkata")
    USE_TRUSTED_TIME = True
