import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "erp-dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'erp.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
    APP_HOST = os.environ.get("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.environ.get("APP_PORT", "5003"))
