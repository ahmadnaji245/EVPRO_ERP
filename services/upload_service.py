from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename


def save_upload(file_storage, folder):
    if not file_storage or not file_storage.filename:
        return None
    upload_root = Path(current_app.config["UPLOAD_FOLDER"])
    target_dir = upload_root / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(file_storage.filename)
    unique_name = f"{uuid4().hex}_{filename}"
    path = target_dir / unique_name
    file_storage.save(path)
    return f"uploads/{folder}/{unique_name}"
