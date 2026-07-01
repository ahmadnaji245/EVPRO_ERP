from database.db import db
from models.brand import Brand
from services.upload_service import save_upload
from utils.validators import normalize_code


def list_brands():
    return Brand.query.order_by(Brand.code).all()


def list_active_brands():
    return Brand.query.filter_by(status="active").order_by(Brand.code).all()


def get_brand(brand_id):
    return Brand.query.get_or_404(brand_id)


def _point_value(value):
    try:
        return float(value or 1)
    except (TypeError, ValueError):
        return 1


def _fill_brand(brand, form, logo_file=None):
    brand.code = normalize_code(form.get("code"))
    brand.name = form.get("name", "").strip()
    brand.color = form.get("color") or "#c5162e"
    brand.point_per_size = _point_value(form.get("point_per_size"))
    brand.status = form.get("status") or "active"
    brand.notes = form.get("notes", form.get("note", "")).strip() or None
    logo_path = save_upload(logo_file, "brands")
    if logo_path:
        brand.logo_path = logo_path
    return brand


def create_brand(form, logo_file=None):
    brand = _fill_brand(Brand(), form, logo_file)
    db.session.add(brand)
    db.session.commit()
    return brand


def update_brand(brand, form, logo_file=None):
    _fill_brand(brand, form, logo_file)
    db.session.commit()
    return brand


def delete_brand(brand):
    brand.is_active = False
    db.session.commit()
    return True


def set_brand_active(brand, is_active):
    brand.is_active = is_active
    db.session.commit()
    return brand
