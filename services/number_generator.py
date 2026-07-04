from datetime import date
from secrets import token_urlsafe

from models.sales_order import SalesOrder


def generate_so_number(brand_code, order_date=None):
    order_date = order_date or date.today()
    compact = order_date.strftime("%y%m%d")
    prefix = f"{brand_code}/{compact}/"
    total = SalesOrder.query.filter(SalesOrder.so_number.like(f"{prefix}%")).count()
    return f"{prefix}{total + 1:04d}"


def generate_customer_code(brand_code, order_date=None):
    order_date = order_date or date.today()
    return f"{brand_code}-{order_date.strftime('%y%m%d')}"


def generate_access_code(brand_code, order_date=None):
    brand_prefix = "".join(ch for ch in str(brand_code or "SO").upper() if ch.isalnum())[:8] or "SO"
    for _ in range(10):
        access_code = f"{brand_prefix}-{token_urlsafe(24)}"
        if not SalesOrder.query.filter_by(access_code=access_code).first():
            return access_code
    raise RuntimeError("Gagal membuat token customer portal yang unik.")


def generate_nota_number(order_date=None):
    from models.nota import Nota

    order_date = order_date or date.today()
    compact = order_date.strftime("%y%m%d")
    prefix = f"{compact}-"
    total = Nota.query.filter(Nota.nota_number.like(f"{prefix}%")).count()
    return f"{prefix}{total + 1:02d}"
