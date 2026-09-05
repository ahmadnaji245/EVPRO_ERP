from pathlib import Path

from flask import current_app

from database.db import db
from models import SalesOrderAttachment
from services.history_service import record_history
from services.upload_service import save_upload


ALLOWED_ATTACHMENT_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def allowed_attachment_image(filename):
    suffix = Path(filename or "").suffix.lower().lstrip(".")
    return suffix in ALLOWED_ATTACHMENT_EXTENSIONS


def add_sales_order_attachment(order, file_storage, title=None, note=None, user=None):
    if not file_storage or not file_storage.filename:
        raise ValueError("File gambar lampiran wajib diisi.")
    if not allowed_attachment_image(file_storage.filename):
        raise ValueError("Lampiran hanya mendukung gambar JPG, JPEG, PNG, atau WEBP.")

    clean_title = str(title or "").strip() or None
    clean_note = str(note or "").strip() or None
    file_path = save_upload(file_storage, f"sales_order_attachments/{order.id}")
    if not file_path:
        raise ValueError("File gambar lampiran wajib diisi.")

    attachment = SalesOrderAttachment(
        sales_order=order,
        file_path=file_path,
        title=clean_title,
        note=clean_note,
        original_filename=file_storage.filename,
        created_by=user,
        created_by_name=getattr(user, "name", None) or getattr(user, "username", None),
    )
    db.session.add(attachment)
    record_history(
        order,
        actor_name=getattr(user, "name", None) or getattr(user, "username", None) or "System",
        action="Tambah Lampiran",
        field_name="attachment",
        new_value=clean_title or file_storage.filename,
        user=user,
        notes=f"Tambah lampiran: {clean_title or 'Lampiran'}",
    )
    db.session.commit()
    return attachment


def get_attachment_for_order(order, attachment_id):
    return SalesOrderAttachment.query.filter_by(id=attachment_id, sales_order_id=order.id).first_or_404()


def delete_sales_order_attachment(order, attachment, user=None):
    title = attachment.title or "Lampiran"
    _delete_uploaded_file(attachment.file_path)
    db.session.delete(attachment)
    record_history(
        order,
        actor_name=getattr(user, "name", None) or getattr(user, "username", None) or "System",
        action="Hapus Lampiran",
        field_name="attachment",
        old_value=title,
        user=user,
        notes=f"Hapus lampiran: {title}",
    )
    db.session.commit()


def _delete_uploaded_file(file_path):
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    stored_path_value = str(file_path or "")
    if not stored_path_value.startswith("uploads/"):
        return
    relative_upload_path = stored_path_value.removeprefix("uploads/")
    stored_path = (
        upload_root.parent / stored_path_value
        if upload_root.name == "uploads"
        else upload_root / relative_upload_path
    ).resolve()
    try:
        stored_path.relative_to(upload_root)
    except ValueError:
        return
    if stored_path.exists():
        stored_path.unlink()
