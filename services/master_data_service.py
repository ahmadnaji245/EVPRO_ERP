from sqlalchemy import func

from database.db import db
from services.sort_order_service import get_next_sort_order


def list_rows(model):
    return model.query.order_by(func.coalesce(model.sort_order, 0).asc(), model.name.asc()).all()


def list_active_rows(model):
    return model.query.filter_by(status="active").order_by(func.coalesce(model.sort_order, 0).asc(), model.name.asc()).all()


def get_row(model, row_id):
    return model.query.get_or_404(row_id)


def validate_master_form(form, model=None, row=None):
    errors = []
    name = form.get("name", "").strip()
    if not name:
        errors.append("Nama data wajib diisi.")
    if model and name:
        query = model.query.filter(model.name == name)
        if row:
            query = query.filter(model.id != row.id)
        if query.first():
            errors.append("Nama data sudah digunakan.")
    return errors


def create_row(model, form):
    row = model(
        name=form.get("name", "").strip(),
        status=form.get("status") or "active",
        sort_order=get_next_sort_order(model),
    )
    _apply_item_options(row, form)
    db.session.add(row)
    db.session.commit()
    return row


def update_row(row, form):
    row.name = form.get("name", "").strip()
    row.status = form.get("status") or "active"
    if not row.sort_order or row.sort_order < 1:
        row.sort_order = get_next_sort_order(type(row))
    _apply_item_options(row, form)
    db.session.commit()
    return row


def delete_row(row):
    row.is_active = False
    db.session.commit()


def set_row_active(row, is_active):
    row.is_active = is_active
    db.session.commit()
    return row


def _apply_item_options(row, form):
    if not hasattr(row, "perlu_upload_gambar"):
        return
    row.perlu_upload_gambar = form.get("perlu_upload_gambar", "0") == "1"
    row.perlu_qc = form.get("perlu_qc", "0") == "1"
