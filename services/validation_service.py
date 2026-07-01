from utils.validators import required
from utils.validators import normalize_code
from models.brand import Brand


def validate_brand_form(form, brand=None):
    errors = []
    if not required(form.get("code")):
        errors.append("Kode brand wajib diisi.")
    if not required(form.get("name")):
        errors.append("Nama brand wajib diisi.")
    code = normalize_code(form.get("code"))
    if code:
        query = Brand.query.filter_by(code=code)
        if brand:
            query = query.filter(Brand.id != brand.id)
        if query.first():
            errors.append("Kode brand sudah digunakan.")
    return errors
