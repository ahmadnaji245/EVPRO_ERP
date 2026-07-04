from pathlib import Path

from flask import current_app

from database.db import db
from models import SalesOrderProductionPhoto
from services.upload_service import save_upload


ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def allowed_photo(filename):
    suffix = Path(filename or "").suffix.lower().lstrip(".")
    return suffix in ALLOWED_PHOTO_EXTENSIONS


def add_production_photos(order, files, uploaded_by=None):
    saved = []
    next_order = _next_sort_order(order)
    folder = f"production_photos/{order.id}"
    for file_storage in files:
        if not file_storage or not file_storage.filename:
            continue
        if not allowed_photo(file_storage.filename):
            raise ValueError("Foto hasil produksi hanya mendukung JPG, PNG, atau WEBP.")
        file_path = save_upload(file_storage, folder)
        if not file_path:
            continue
        photo = SalesOrderProductionPhoto(
            sales_order=order,
            file_path=file_path,
            original_filename=file_storage.filename,
            sort_order=next_order,
            uploaded_by=uploaded_by,
        )
        db.session.add(photo)
        saved.append(photo)
        next_order += 1
    if saved:
        db.session.commit()
    return saved


def delete_production_photo(photo):
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    file_path = str(photo.file_path or "")
    if file_path.startswith("uploads/"):
        relative_upload_path = file_path.removeprefix("uploads/")
        stored_path = (
            upload_root.parent / file_path
            if upload_root.name == "uploads"
            else upload_root / relative_upload_path
        ).resolve()
        try:
            stored_path.relative_to(upload_root)
        except ValueError:
            stored_path = None
        if stored_path and stored_path.exists():
            stored_path.unlink()
    db.session.delete(photo)
    db.session.commit()


def get_photo_for_order(order, photo_id):
    return SalesOrderProductionPhoto.query.filter_by(id=photo_id, sales_order_id=order.id).first_or_404()


def _next_sort_order(order):
    current = [photo.sort_order for photo in order.production_photos]
    return (max(current) if current else 0) + 1
