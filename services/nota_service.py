from datetime import date, datetime

from sqlalchemy import func, or_

from database.db import db
from models import Brand, Nota, NotaCustomer, NotaItem, NotaPayment, NotaProduct, SalesOrder
from services.number_generator import generate_nota_number


NOTA_STATUSES = (
    "Belum DP",
    "DP",
    "Lunas",
    "Desain",
    "Produksi",
    "Selesai",
    "Diambil",
)

DEFAULT_NOTA_PRODUCTS = [
    ("FP", "Setelan full printing", 135000),
    ("LP1", "Tambahan lengan panjang", 15000),
    ("BE", "Bahan embosh", 5000),
    ("D30", "Diskon Rp30.000", -30000),
    ("DR", "Diskon regular", -10000),
    ("JA", "Diskon jersey anak", -10000),
    ("SL", "Diskon special line", -10000),
]


def list_brands():
    return Brand.query.filter_by(status="active").order_by(Brand.name).all()


def list_customers():
    return NotaCustomer.query.order_by(NotaCustomer.name).all()


def list_products():
    return NotaProduct.query.order_by(NotaProduct.code).all()


def list_products_as_dicts():
    return [
        {"id": product.id, "code": product.code, "description": product.description, "price": product.price}
        for product in list_products()
    ]


def list_customers_as_dicts():
    return [
        {
            "id": customer.id,
            "brand_id": customer.brand_id,
            "name": customer.name,
            "team_name": customer.team_name,
            "phone": customer.phone,
            "address": customer.address,
        }
        for customer in list_customers()
    ]


def list_notas(search=None):
    search = search or {}
    query = Nota.query.join(NotaCustomer).join(Brand).outerjoin(SalesOrder, Nota.so_id == SalesOrder.id)
    q = str(search.get("q") or "").strip()
    status = str(search.get("status") or "").strip()
    brand_id = str(search.get("brand_id") or "").strip()

    if q:
        needle = f"%{q}%"
        query = query.filter(
            or_(
                Nota.nota_number.ilike(needle),
                NotaCustomer.name.ilike(needle),
                Nota.team_name.ilike(needle),
                NotaCustomer.phone.ilike(needle),
                SalesOrder.so_number.ilike(needle),
            )
        )
    if status:
        query = query.filter(Nota.status == status)
    if brand_id.isdigit():
        query = query.filter(Nota.brand_id == int(brand_id))
    return query.order_by(Nota.order_date.desc(), Nota.id.desc()).all()


def get_nota(nota_id):
    return Nota.query.get_or_404(nota_id)


def get_nota_by_so_id(so_id):
    if not str(so_id or "").isdigit():
        return None
    return Nota.query.filter_by(so_id=int(so_id)).first()


def get_product_by_code(code):
    return NotaProduct.query.filter(func.upper(NotaProduct.code) == str(code or "").strip().upper()).first()


def totals(nota):
    return {"total": nota.total, "paid": nota.paid, "remaining": nota.remaining}


def item_rows_for_form(nota=None):
    if not nota:
        return []
    return [
        {
            "product_code": item.product_code,
            "quantity": item.quantity,
            "description": item.description,
            "price": item.price,
            "subtotal": item.subtotal,
        }
        for item in sorted(nota.items, key=lambda item: item.sort_order)
    ]


def posted_item_rows(form):
    codes = form.getlist("product_code[]")
    quantities = form.getlist("quantity[]")
    rows = []
    for index, code in enumerate(codes):
        rows.append(
            {
                "product_code": code,
                "quantity": quantities[index] if index < len(quantities) else "",
            }
        )
    return rows


def form_data_from_sales_order(sales_order):
    customer_access = sales_order.customer_access
    order_date = sales_order.created_at.date() if sales_order.created_at else date.today()
    return {
        "so_id": sales_order.id,
        "brand_id": sales_order.brand_id,
        "order_date": order_date.isoformat(),
        "status": "Belum DP",
        "customer_name": customer_access.customer_name if customer_access else sales_order.team_name,
        "team_name": sales_order.team_name,
        "phone": customer_access.customer_phone if customer_access else "",
        "address": "",
        "notes": f"Dibuat dari Sales Order {sales_order.so_number}",
    }


def item_rows_from_sales_order(sales_order):
    total_size = sales_order.total_size
    if total_size <= 0:
        return []
    if not get_product_by_code("FP"):
        return []
    return [{"product_code": "FP", "quantity": total_size}]


def billing_status_for_sales_order(sales_order):
    nota = get_nota_by_so_id(sales_order.id)
    if not nota:
        return "Belum Ada Nota"
    if nota.status == "Lunas" or (nota.total > 0 and nota.remaining <= 0):
        return "Lunas"
    if nota.status == "DP" or nota.paid > 0:
        return "DP"
    return "Nota Dibuat"


def parse_item_rows(form):
    codes = form.getlist("product_code[]")
    quantities = form.getlist("quantity[]")
    items = []
    errors = []
    for index, code in enumerate(codes, start=1):
        code = str(code or "").strip().upper()
        quantity_raw = str(quantities[index - 1] if index - 1 < len(quantities) else "").strip()
        if not code and not quantity_raw:
            continue
        if not code:
            errors.append(f"Baris {index}: kode produk harus diisi.")
            continue
        if not quantity_raw.isdigit() or int(quantity_raw) <= 0:
            errors.append(f"Baris {index}: qty harus angka lebih dari 0.")
            continue
        product = get_product_by_code(code)
        if product is None:
            errors.append(f"Baris {index}: kode produk {code} belum ada di database.")
            continue
        items.append(
            {
                "product_id": product.id,
                "code": product.code,
                "description": product.description,
                "price": product.price,
                "quantity": int(quantity_raw),
            }
        )
    if not items:
        errors.append("Minimal satu item produk harus diisi.")
    return items, errors


def validate_nota_form(form):
    errors = []
    if not _get_brand(form.get("brand_id")):
        errors.append("Brand wajib dipilih.")
    if not str(form.get("order_date") or "").strip():
        errors.append("Tanggal order wajib diisi.")
    elif not _parse_date(form.get("order_date")):
        errors.append("Tanggal order tidak valid.")
    if str(form.get("status") or "").strip() not in NOTA_STATUSES:
        errors.append("Status order tidak valid.")
    if not str(form.get("customer_name") or "").strip():
        errors.append("Nama customer wajib diisi.")
    if not str(form.get("team_name") or "").strip():
        errors.append("Nama tim wajib diisi.")
    _, item_errors = parse_item_rows(form)
    errors.extend(item_errors)
    return errors


def create_nota(form, user=None):
    items, errors = parse_item_rows(form)
    if errors:
        raise ValueError("\n".join(errors))
    order_date = _parse_date(form.get("order_date"))
    customer = _save_customer(form)
    so_id = _parse_so_id(form.get("so_id"))
    existing_nota = get_nota_by_so_id(so_id) if so_id else None
    if existing_nota:
        return existing_nota
    nota = Nota(
        nota_number=generate_nota_number(order_date),
        brand_id=int(form.get("brand_id")),
        order_date=order_date,
        customer=customer,
        team_name=str(form.get("team_name") or "").strip(),
        status=str(form.get("status") or "Belum DP").strip(),
        notes=str(form.get("notes") or "").strip() or None,
        so_id=so_id,
        created_by_id=user.id if user else None,
    )
    _replace_items(nota, items)
    db.session.add(nota)
    db.session.commit()
    return nota


def update_nota(nota, form):
    items, errors = parse_item_rows(form)
    if errors:
        raise ValueError("\n".join(errors))
    customer = _save_customer(form)
    nota.brand_id = int(form.get("brand_id"))
    nota.order_date = _parse_date(form.get("order_date"))
    nota.customer = customer
    nota.team_name = str(form.get("team_name") or "").strip()
    nota.status = str(form.get("status") or "").strip()
    nota.notes = str(form.get("notes") or "").strip() or None
    so_id = _parse_so_id(form.get("so_id"))
    if so_id and so_id != nota.so_id:
        existing_nota = get_nota_by_so_id(so_id)
        if existing_nota:
            raise ValueError("Sales Order ini sudah memiliki Nota.")
    nota.so_id = so_id
    _replace_items(nota, items)
    db.session.commit()
    return nota


def add_payment(nota, form):
    payment_date = _parse_date(form.get("payment_date"))
    amount = _parse_int(form.get("amount"))
    if not payment_date:
        raise ValueError("Tanggal pembayaran wajib diisi.")
    if amount <= 0:
        raise ValueError("Nominal pembayaran harus lebih dari 0.")
    db.session.add(
        NotaPayment(
            nota=nota,
            payment_date=payment_date,
            amount=amount,
            description=str(form.get("description") or "").strip() or None,
        )
    )
    db.session.commit()


def update_status(nota, status):
    if status not in NOTA_STATUSES:
        raise ValueError("Status order tidak valid.")
    nota.status = status
    db.session.commit()


def seed_default_nota_products():
    existing = {product.code.upper(): product for product in NotaProduct.query.all()}
    for code, description, price in DEFAULT_NOTA_PRODUCTS:
        product = existing.get(code.upper())
        if product:
            product.description = description
            product.price = price
        else:
            db.session.add(NotaProduct(code=code, description=description, price=price))


def _save_customer(form):
    brand_id = int(form.get("brand_id"))
    customer_id = form.get("customer_id")
    customer = NotaCustomer.query.get(int(customer_id)) if str(customer_id or "").isdigit() else None
    if not customer:
        customer = NotaCustomer()
        db.session.add(customer)
    customer.brand_id = brand_id
    customer.name = str(form.get("customer_name") or "").strip()
    customer.team_name = str(form.get("team_name") or "").strip()
    customer.phone = str(form.get("phone") or "").strip() or None
    customer.address = str(form.get("address") or "").strip() or None
    return customer


def _replace_items(nota, items):
    nota.items.clear()
    for index, item in enumerate(items, start=1):
        nota.items.append(
            NotaItem(
                product_id=item["product_id"],
                product_code=item["code"],
                description=item["description"],
                price=int(item["price"]),
                quantity=int(item["quantity"]),
                subtotal=int(item["price"]) * int(item["quantity"]),
                sort_order=index,
            )
        )


def _get_brand(brand_id):
    if not str(brand_id or "").isdigit():
        return None
    return Brand.query.get(int(brand_id))


def _parse_date(value):
    if isinstance(value, date):
        return value
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _parse_so_id(value):
    if not str(value or "").isdigit():
        return None
    sales_order = SalesOrder.query.filter_by(id=int(value), is_deleted=False).first()
    return sales_order.id if sales_order else None
