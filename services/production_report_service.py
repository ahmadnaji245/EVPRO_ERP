from datetime import date, datetime

from sqlalchemy import extract
from sqlalchemy.orm import selectinload

from database.db import db
from models import Brand, MasterVendor, SalesOrder, SalesOrderDesign, SalesOrderPlayer
from services.item_service import component_key, design_components, qc_enabled_components_for_order
from services.production_service import FINISHED_PRODUCTION_STATUSES, effective_deadline, production_status
from utils.constants import PRODUCTION_STATUSES


HANDOVER_STATUS_OPTIONS = (
    ("all", "Semua Handover"),
    ("pending", "Belum Handover"),
    ("done", "Sudah Handover"),
)

PRODUCTION_STATUS_FILTERS = (
    ("all", "Semua Status"),
    ("running", "Sedang Berjalan"),
    ("finish", "Selesai"),
)


def production_tracking_report(filters=None):
    filters = _normalize_filters(filters or {})
    orders = _filtered_orders(filters)
    rows = [_tracking_row(order) for order in orders]
    return {
        "filters": filters,
        "rows": rows,
        "summary": _summary(rows),
        "brand_options": _brand_options(),
        "vendor_options": _vendor_options(orders),
        "status_options": _status_options(),
        "handover_status_options": HANDOVER_STATUS_OPTIONS,
        "month_options": _month_options(),
        "year_options": _year_options(),
    }


def _filtered_orders(filters):
    query = (
        SalesOrder.query.options(
            selectinload(SalesOrder.brand),
            selectinload(SalesOrder.designs)
            .selectinload(SalesOrderDesign.players)
            .selectinload(SalesOrderPlayer.checklist),
            selectinload(SalesOrder.designs)
            .selectinload(SalesOrderDesign.players)
            .selectinload(SalesOrderPlayer.qc_checklist),
        )
        .filter(SalesOrder.is_deleted.is_(False), SalesOrder.approval_status == "approved")
    )

    if filters["brand_id"]:
        query = query.filter(SalesOrder.brand_id == filters["brand_id"])
    if filters["vendor"]:
        query = query.filter(SalesOrder.production_vendor == filters["vendor"])

    status_filter = filters["status"]
    if status_filter == "running":
        query = query.filter(SalesOrder.production_status.notin_(FINISHED_PRODUCTION_STATUSES))
    elif status_filter == "finish":
        query = query.filter(SalesOrder.production_status.in_(FINISHED_PRODUCTION_STATUSES))
    elif status_filter not in {"all", ""}:
        query = query.filter(SalesOrder.production_status == status_filter)

    if filters["handover_status"] == "pending":
        query = query.filter(SalesOrder.tanggal_pengambilan.is_(None))
    elif filters["handover_status"] == "done":
        query = query.filter(SalesOrder.tanggal_pengambilan.isnot(None))

    if filters["year"]:
        query = query.filter(extract("year", SalesOrder.approved_at) == filters["year"])
    if filters["month"]:
        query = query.filter(extract("month", SalesOrder.approved_at) == filters["month"])

    search = filters["q"].casefold()
    orders = query.order_by(SalesOrder.approved_at.desc(), SalesOrder.created_at.desc(), SalesOrder.id.desc()).all()
    if search:
        orders = [order for order in orders if _matches_search(order, search)]
    return orders


def _tracking_row(order):
    status = production_status(order)
    deadline = effective_deadline(order)
    started_at = order.production_assigned_at or order.printing_started_at or order.approved_at
    completed_at = order.tanggal_finish_produksi if status == "Finish" else None
    handover_done = bool(order.tanggal_pengambilan)
    progress = _progress(order)
    return {
        "order": order,
        "so_number": order.so_number,
        "tanggal_masuk": order.approved_at or order.created_at,
        "team_name": order.team_name,
        "brand": order.brand.name if order.brand else "-",
        "brand_code": order.brand.code if order.brand else "-",
        "total_qty": order.total_size,
        "vendor": order.production_vendor or "-",
        "production_started_at": started_at,
        "deadline": deadline,
        "deadline_state": _deadline_state(deadline, completed_at, status),
        "progress": progress,
        "production_status": status,
        "completed_at": completed_at,
        "handover_status": "Sudah Handover" if handover_done else "Belum Handover",
        "handover_date": order.tanggal_pengambilan,
        "is_finished": status == "Finish",
        "is_waiting_handover": status == "Finish" and not handover_done,
    }


def _progress(order):
    players = [
        player
        for design in sorted(order.designs, key=lambda row: (row.sort_order, row.id or 0))
        for player in sorted(design.players, key=lambda row: (row.sort_order, row.id or 0))
    ]
    total = len(players)
    setting_done = sum(1 for player in players if player.checklist and player.checklist.setting_done)
    qc_done = sum(1 for player in players if _player_qc_done(player, order))
    return {
        "total": total,
        "setting_done": setting_done,
        "qc_done": qc_done,
        "setting_label": f"{setting_done}/{total}",
        "qc_label": f"{qc_done}/{total}",
    }


def _player_qc_done(player, order):
    if player.checklist and player.checklist.qc_done:
        return True
    qc_checklist = player.qc_checklist
    if not qc_checklist:
        return False
    enabled_components = set(qc_enabled_components_for_order(order))
    player_components = [component for component in design_components(player.design) if component in enabled_components]
    if not player_components:
        return bool(qc_checklist.qc_jersey or qc_checklist.qc_celana)
    qc_data = _qc_data(qc_checklist)
    return all(bool(qc_data.get(component_key(component))) for component in player_components)


def _qc_data(qc_checklist):
    if not qc_checklist:
        return {}
    if qc_checklist.qc_data:
        import json

        try:
            return json.loads(qc_checklist.qc_data)
        except (TypeError, ValueError):
            return {}
    return {
        "jersey": bool(qc_checklist.qc_jersey),
        "celana": bool(qc_checklist.qc_celana),
    }


def _deadline_state(deadline, completed_at, status):
    if not deadline:
        return "none"
    if status == "Finish":
        if isinstance(completed_at, datetime):
            return "done_late" if completed_at.date() > deadline else "done"
        return "done"
    compare_date = date.today()
    if compare_date > deadline:
        return "late"
    days_left = (deadline - date.today()).days
    if days_left < 0:
        return "late"
    if days_left <= 3:
        return "soon"
    return "normal"


def _summary(rows):
    return {
        "total": len(rows),
        "running": sum(1 for row in rows if not row["is_finished"]),
        "finished": sum(1 for row in rows if row["is_finished"]),
        "waiting_handover": sum(1 for row in rows if row["is_waiting_handover"]),
    }


def _brand_options():
    return Brand.query.order_by(Brand.name.asc()).all()


def _vendor_options(orders):
    names = []
    seen = set()
    for vendor in MasterVendor.query.order_by(db.func.coalesce(MasterVendor.sort_order, 0).asc(), MasterVendor.name.asc()).all():
        if vendor.name and vendor.name.casefold() not in seen:
            names.append(vendor.name)
            seen.add(vendor.name.casefold())
    for order in orders:
        vendor = str(order.production_vendor or "").strip()
        if vendor and vendor.casefold() not in seen:
            names.append(vendor)
            seen.add(vendor.casefold())
    return names


def _status_options():
    return list(PRODUCTION_STATUS_FILTERS) + [(status, status) for status in PRODUCTION_STATUSES]


def _month_options():
    return [
        (1, "Januari"),
        (2, "Februari"),
        (3, "Maret"),
        (4, "April"),
        (5, "Mei"),
        (6, "Juni"),
        (7, "Juli"),
        (8, "Agustus"),
        (9, "September"),
        (10, "Oktober"),
        (11, "November"),
        (12, "Desember"),
    ]


def _year_options():
    years = {
        row[0]
        for row in db.session.query(extract("year", SalesOrder.approved_at))
        .filter(SalesOrder.is_deleted.is_(False), SalesOrder.approval_status == "approved", SalesOrder.approved_at.isnot(None))
        .all()
        if row[0]
    }
    years.add(date.today().year)
    return sorted((int(year) for year in years), reverse=True)


def _normalize_filters(filters):
    return {
        "month": _parse_int(filters.get("month")),
        "year": _parse_int(filters.get("year")),
        "brand_id": _parse_int(filters.get("brand_id")),
        "vendor": str(filters.get("vendor") or "").strip(),
        "status": str(filters.get("status") or "all").strip() or "all",
        "handover_status": str(filters.get("handover_status") or "all").strip() or "all",
        "q": str(filters.get("q") or "").strip(),
    }


def _parse_int(value):
    try:
        return int(value) if str(value or "").strip() else None
    except (TypeError, ValueError):
        return None


def _matches_search(order, search):
    values = [
        order.so_number,
        order.team_name,
        order.brand.name if order.brand else "",
        order.brand.code if order.brand else "",
        order.production_vendor,
        production_status(order),
    ]
    return any(search in str(value or "").casefold() for value in values)
