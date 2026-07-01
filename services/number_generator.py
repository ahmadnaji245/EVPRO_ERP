from datetime import date

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
    order_date = order_date or date.today()
    total = SalesOrder.query.filter(SalesOrder.access_code.like(f"{order_date.strftime('%y%m%d')}-%")).count()
    return f"{order_date.strftime('%y%m%d')}-{total + 1:02d}"


def generate_nota_number(order_date=None):
    from models.nota import Nota

    order_date = order_date or date.today()
    compact = order_date.strftime("%y%m%d")
    prefix = f"{compact}-"
    total = Nota.query.filter(Nota.nota_number.like(f"{prefix}%")).count()
    return f"{prefix}{total + 1:02d}"
