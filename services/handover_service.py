from datetime import date, datetime

from sqlalchemy import extract

from database.db import db
from models import SalesOrder
from services.nota_service import calculate_invoice_status, get_nota_by_so_id
from utils.constants import normalize_production_status


MONTH_NAMES = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}


def handover_summary():
    pending_rows = pending_pickup_rows()
    today = date.today()
    return {
        "pending_count": len(pending_rows),
        "picked_this_month": len(picked_up_rows(today.month, today.year)),
        "pending_remaining": sum(row["nota"]["remaining"] for row in pending_rows),
    }


def pending_pickup_rows():
    orders = (
        SalesOrder.query.filter_by(is_deleted=False)
        .filter(SalesOrder.tanggal_pengambilan.is_(None))
        .order_by(SalesOrder.tanggal_finish_produksi.asc(), SalesOrder.production_status_updated_at.asc(), SalesOrder.id.asc())
        .all()
    )
    return [_pending_row(order) for order in orders if _is_finished(order)]


def picked_up_rows(month=None, year=None):
    query = SalesOrder.query.filter_by(is_deleted=False).filter(SalesOrder.tanggal_pengambilan.isnot(None))
    if month and year:
        start_date, end_date = pickup_month_period(month, year)
        query = query.filter(
            SalesOrder.tanggal_pengambilan >= start_date,
            SalesOrder.tanggal_pengambilan < end_date,
        )
    elif month:
        query = query.filter(extract("month", SalesOrder.tanggal_pengambilan) == month)
    elif year:
        query = query.filter(extract("year", SalesOrder.tanggal_pengambilan) == year)
    orders = (
        query
        .order_by(SalesOrder.tanggal_pengambilan.desc(), SalesOrder.id.desc())
        .all()
    )
    return [_picked_row(order) for order in orders]


def picked_up_monthly_summary(month, year):
    rows = picked_up_rows(month, year)
    return {
        "total_picked": len(rows),
        "total_nota": sum(row["nota"]["total"] for row in rows),
        "total_paid": sum(row["nota"]["paid"] for row in rows),
    }


def handover_filter_from_args(args):
    today = date.today()
    raw_month = str(args.get("bulan", today.month)).strip()
    raw_year = str(args.get("tahun", today.year)).strip()
    month = None if raw_month == "all" else _parse_int(raw_month, today.month)
    year = None if raw_year == "all" else _parse_int(raw_year, today.year)
    if month is not None and (month < 1 or month > 12):
        month = today.month
    if year is not None and (year < 2000 or year > today.year + 5):
        year = today.year
    return month, year


def pickup_month_period(month, year):
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    return start_date, end_date


def month_label(month, year):
    return f"{MONTH_NAMES.get(int(month), month)} {year}"


def handover_period_label(month, year):
    if month and year:
        return month_label(month, year)
    if month:
        return f"{MONTH_NAMES.get(int(month), month)} - Semua Tahun"
    if year:
        return f"Semua Bulan {year}"
    return "Semua Bulan - Semua Tahun"


def year_options(selected_year=None):
    current_year = date.today().year
    years = {
        row[0]
        for row in db.session.query(extract("year", SalesOrder.tanggal_pengambilan))
        .filter(SalesOrder.is_deleted.is_(False), SalesOrder.tanggal_pengambilan.isnot(None))
        .all()
        if row[0]
    }
    years.add(current_year)
    if selected_year:
        years.add(int(selected_year))
    return sorted((int(year) for year in years), reverse=True)


def get_handover_order(sales_order_id):
    return SalesOrder.query.filter_by(id=sales_order_id, is_deleted=False).first_or_404()


def mark_picked_up(order, form, user):
    pickup_date = _parse_date(form.get("tanggal_pengambilan"))
    picked_by = str(form.get("diambil_oleh") or "").strip()
    note = str(form.get("catatan_pengambilan") or "").strip()

    if not pickup_date:
        raise ValueError("Tanggal pengambilan wajib diisi.")
    if not picked_by:
        raise ValueError("Diambil oleh wajib diisi.")
    if not _is_finished(order):
        raise ValueError("Serah terima hanya bisa diproses untuk SO dengan status produksi Finish.")

    order.tanggal_pengambilan = pickup_date
    order.diambil_oleh = picked_by
    order.catatan_pengambilan = note or None
    order.serah_terima_admin_id = user.id if user else None
    db.session.commit()
    return order


def default_pickup_date():
    return date.today().isoformat()


def _pending_row(order):
    nota = get_nota_by_so_id(order.id)
    return {
        "order": order,
        "finish_at": order.tanggal_finish_produksi or order.production_status_updated_at,
        "nota": _nota_snapshot(nota),
    }


def _picked_row(order):
    nota = get_nota_by_so_id(order.id)
    admin = order.serah_terima_admin
    return {
        "order": order,
        "pickup_date": order.tanggal_pengambilan,
        "picked_by": order.diambil_oleh or "-",
        "admin_name": admin.name if admin else "-",
        "note": order.catatan_pengambilan or "-",
        "nota": _nota_snapshot(nota),
    }


def _nota_snapshot(nota):
    if not nota:
        return {
            "nota": None,
            "total": 0,
            "paid": 0,
            "remaining": 0,
            "status": "-",
            "is_paid": False,
        }
    remaining = max(nota.remaining, 0)
    status = calculate_invoice_status(nota)
    is_paid = status == "Lunas"
    return {
        "nota": nota,
        "total": nota.total,
        "paid": nota.paid,
        "remaining": remaining,
        "status": status,
        "is_paid": is_paid,
    }


def _is_finished(order):
    return normalize_production_status(order.production_status) == "Finish"


def _parse_date(value):
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Tanggal pengambilan tidak valid.") from exc


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
