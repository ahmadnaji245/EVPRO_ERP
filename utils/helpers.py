from pathlib import Path

from flask import current_app

from utils.constants import UPLOAD_SUBFOLDERS


def ensure_upload_folders():
    upload_root = Path(current_app.config["UPLOAD_FOLDER"])
    for folder in UPLOAD_SUBFOLDERS:
        (upload_root / folder).mkdir(parents=True, exist_ok=True)


def active_class(endpoint_prefix):
    from flask import request

    return "active" if request.endpoint and request.endpoint.startswith(endpoint_prefix) else ""
