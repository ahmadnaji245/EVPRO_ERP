import json
from datetime import date, datetime, time, timedelta

from database.db import db
from models import Brand, CustomerAccess, QcChecklist, SalesOrder, SalesOrderDesign, SalesOrderPlayer
from services.item_service import component_key, design_components, qc_enabled_components_for_order
from utils.constants import PRODUCTION_STATUSES, PRODUCTION_VENDORS, normalize_production_status, sort_players_by_size


ACTIVE_PRODUCTION_STATUSES = [status for status in PRODUCTION_STATUSES if status != "Finish"]
VENDOR_PRINT_EXCLUDED_STATUSES = {
    "Terkirim dari Vendor",
    "Packing",
    "Finish",
}
VENDOR_RETURNED_STATUSES = {"Terkirim dari Vendor", "Barang Masuk", "QC"}


def list_production_orders(search=None):
    orders = (
        SalesOrder.query.filter_by(is_deleted=False, approval_status="approved")
        .order_by(SalesOrder.deadline.asc().nullslast(), SalesOrder.created_at.asc(), SalesOrder.so_number.desc(), SalesOrder.id.desc())
        .all()
    )
    search_value = str(search or "").strip().casefold()
    if not search_value:
        return orders
    return [order for order in orders if _matches_search(order, search_value)]


def production_summary(orders):
    today = datetime.utcnow().date()
    return {
        "waiting_assign": sum(1 for order in orders if production_status(order) == "Approval Customer"),
        "in_progress": sum(1 for order in orders if production_status(order) in {"Setting", "Printing", "Jahit"}),
        "deadline_today": sum(1 for order in orders if effective_deadline(order) == today and production_status(order) != "Finish"),
        "warehouse_qc": sum(1 for order in orders if production_status(order) in {"QC", "Packing"}),
        "done": sum(1 for order in orders if production_status(order) == "Finish"),
        "late": sum(1 for order in orders if is_late(order, today)),
    }


def vendor_summary(orders):
    today = datetime.utcnow().date()
    rows = []
    for vendor in PRODUCTION_VENDORS:
        vendor_orders = [order for order in orders if order.production_vendor == vendor and production_status(order) != "Finish"]
        rows.append(
            {
                "name": vendor,
                "total_active": len(vendor_orders),
                "deadline_today": sum(1 for order in vendor_orders if effective_deadline(order) == today),
                "late": sum(
                    1
                    for order in vendor_orders
                    if effective_deadline(order) and effective_deadline(order) < today
                ),
                "qc_issue": sum(
                    1
                    for order in vendor_orders
                    if production_status(order) == "QC" or order.shortage_note or order.qc_note
                ),
            }
        )
    return rows


def vendor_print_rows(vendor):
    vendor = validate_vendor(vendor)
    orders = (
        SalesOrder.query.filter_by(is_deleted=False, approval_status="approved", production_vendor=vendor)
        .all()
    )
    active_orders = [order for order in orders if _include_in_vendor_print(order)]
    active_orders = sorted(
        active_orders,
        key=lambda order: (
            effective_deadline(order) or date.max,
            order.approved_at or order.created_at or datetime.min,
            order.id or 0,
        ),
    )
    return [_vendor_print_row(order) for order in active_orders]


def prepare_qc_checklists(order):
    existing = {checklist.sales_order_player_id: checklist for checklist in order.qc_checklists}
    created = False
    for player in _order_players(order):
        if player.id not in existing:
            db.session.add(QcChecklist(sales_order_id=order.id, sales_order_player_id=player.id))
            created = True
    if created:
        db.session.commit()
    return {checklist.sales_order_player_id: checklist for checklist in order.qc_checklists}


def qc_checklist_rows(order):
    checklists = prepare_qc_checklists(order)
    qc_components = qc_enabled_components_for_order(order)
    rows = {}
    for player in _order_players(order):
        key = _player_group_key(player)
        row = rows.setdefault(
            key,
            {
                "item": [],
                "name": player.player_name,
                "number": player.player_number,
                "size": player.size,
                "notes": [],
                "checks": {
                    component: {"player_id": None, "checked": False}
                    for component in qc_components
                },
            },
        )
        item_name = player.design.item_name or "-"
        if item_name not in row["item"]:
            row["item"].append(item_name)
        if player.notes and player.notes != "-" and player.notes not in row["notes"]:
            row["notes"].append(player.notes)

        checklist = checklists.get(player.id)
        qc_data = _checklist_qc_data(checklist)
        for component in design_components(player.design):
            if component not in row["checks"]:
                continue
            row["checks"][component]["player_id"] = player.id
            row["checks"][component]["checked"] = bool(qc_data.get(component_key(component)))

    return list(rows.values()), qc_components


def qc_checklist_rows_from_form(order, form):
    rows, qc_components = qc_checklist_rows(order)
    checked = {
        component: set(form.getlist(f"qc_{component_key(component)}"))
        for component in qc_components
    }
    for row in rows:
        for component in qc_components:
            check = row["checks"].get(component)
            if check and check["player_id"]:
                check["checked"] = str(check["player_id"]) in checked[component]
    return rows, qc_components


def save_qc_checklist(order, form):
    checklist_by_player = prepare_qc_checklists(order)
    checked = {
        component: set(form.getlist(f"qc_{component_key(component)}"))
        for component in qc_enabled_components_for_order(order)
    }
    qc_note = str(form.get("qc_note") or "").strip()
    shortage_note = calculate_shortage_note_from_checked(order, checked)
    if shortage_note and not qc_note:
        raise ValueError("Ada item yang belum lolos QC. Isi keterangan QC terlebih dahulu.")

    now = datetime.utcnow()
    for player in _order_players(order):
        checklist = checklist_by_player[player.id]
        player_key = str(player.id)
        qc_data = {}
        for component in design_components(player.design):
            if component not in checked:
                continue
            qc_data[component_key(component)] = player_key in checked[component]
        checklist.qc_data = json.dumps(qc_data, sort_keys=True)
        checklist.qc_jersey = bool(qc_data.get("jersey"))
        checklist.qc_celana = bool(qc_data.get("celana"))
        checklist.updated_at = now
    order.shortage_note = shortage_note
    order.qc_note = qc_note or None
    _set_stage(order, "QC" if shortage_note else "Packing")
    db.session.commit()
    return order.shortage_note


def calculate_shortage_note(order):
    checked = {
        component: set()
        for component in qc_enabled_components_for_order(order)
    }
    for checklist in order.qc_checklists:
        qc_data = _checklist_qc_data(checklist)
        for component in checked:
            if qc_data.get(component_key(component)):
                checked[component].add(str(checklist.sales_order_player_id))
    return calculate_shortage_note_from_checked(order, checked)


def calculate_shortage_note_from_checked(order, checked):
    missing = {component: 0 for component in qc_enabled_components_for_order(order)}
    for player in _order_players(order):
        player_key = str(player.id)
        for component in design_components(player.design):
            if component not in missing:
                continue
            if player_key not in checked.get(component, set()):
                missing[component] += 1

    parts = []
    for component, qty in missing.items():
        if qty:
            parts.append(f"{component} kurang/reject {qty} pcs")
    return ", ".join(parts)


def seed_production_sample_data():
    today = datetime.utcnow().date()
    samples = [
        {
            "requested_so_number": "EVPRO/260701/0002",
            "team_name": "GARUDA FC",
            "brand_code": "EVPRO",
            "brand_name": "Evpro",
            "qty_jrsy": 24,
            "qty_cln": 24,
            "vendor": "Mas Amar",
            "status": "Jahit",
            "deadline": today - timedelta(days=1),
            "assigned_at": today - timedelta(days=4),
        },
        {
            "requested_so_number": "EVPRO/260701/0003",
            "team_name": "BINTANG TIMUR",
            "brand_code": "RDR",
            "brand_name": "RDR Apparel",
            "qty_jrsy": 18,
            "qty_cln": 18,
            "vendor": "Mas Amar",
            "status": "Potong",
            "deadline": today + timedelta(days=1),
            "assigned_at": today - timedelta(days=3),
        },
        {
            "requested_so_number": "EVPRO/260701/0004",
            "team_name": "RAJAWALI MUDA",
            "brand_code": "ONS",
            "brand_name": "Onside",
            "qty_jrsy": 30,
            "qty_cln": 0,
            "vendor": "Mas Amar",
            "status": "Terkirim dari Vendor",
            "deadline": today + timedelta(days=2),
            "assigned_at": today - timedelta(days=2),
        },
        {
            "requested_so_number": "EVPRO/260701/0005",
            "team_name": "SATRIA UNITED",
            "brand_code": "EVPRO",
            "brand_name": "Evpro",
            "qty_jrsy": 20,
            "qty_cln": 20,
            "vendor": "Mas Syukron",
            "status": "Printing",
            "deadline": today + timedelta(days=2),
            "assigned_at": today - timedelta(days=3),
        },
        {
            "requested_so_number": "EVPRO/260701/0006",
            "team_name": "ELANG PUTRA",
            "brand_code": "RDR",
            "brand_name": "RDR Apparel",
            "qty_jrsy": 15,
            "qty_cln": 15,
            "vendor": "Mas Syukron",
            "status": "Finishing",
            "deadline": today + timedelta(days=4),
            "assigned_at": today - timedelta(days=2),
        },
        {
            "requested_so_number": "EVPRO/260701/0007",
            "team_name": "PERSADA FC",
            "brand_code": "ARM",
            "brand_name": "Armor",
            "qty_jrsy": 28,
            "qty_cln": 28,
            "vendor": "Mas Syukron",
            "status": "Jahit",
            "deadline": today + timedelta(days=5),
            "assigned_at": today - timedelta(days=2),
        },
    ]

    created = []
    existing = []
    for sample in samples:
        marker = f"SAMPLE_PRODUCTION_VENDOR_TABLE:{sample['team_name']}"
        previous_sample = SalesOrder.query.filter_by(notes=marker).first()
        if previous_sample:
            existing.append(previous_sample.so_number)
            continue

        so_number = _available_sample_so_number(sample["requested_so_number"])
        if so_number != sample["requested_so_number"]:
            existing.append(sample["requested_so_number"])

        brand = _get_or_create_sample_brand(sample["brand_code"], sample["brand_name"])
        order = SalesOrder(
            so_number=so_number,
            team_name=sample["team_name"],
            brand_id=brand.id,
            customer_code=f"SAMPLE-{sample['team_name'].replace(' ', '-')[:24]}",
            access_code=f"sample-prod-{so_number.replace('/', '-').lower()}",
            material="Dryfit",
            pattern="Reguler",
            grade="A",
            production_days=7,
            deadline=sample["deadline"] + timedelta(days=3),
            instructions="Default",
            notes=marker,
            approval_status="approved",
            approved_by="Sample Seed",
            approved_source="admin",
            approved_at=datetime.combine(sample["assigned_at"], time.min),
            production_status=sample["status"],
            production_status_updated_at=datetime.combine(sample["assigned_at"], time.min),
            production_vendor=sample["vendor"],
            production_vendor_deadline=sample["deadline"],
            production_assigned_at=datetime.combine(sample["assigned_at"], time(hour=9)),
            created_at=datetime.combine(sample["assigned_at"], time.min),
        )
        order.customer_access = CustomerAccess(
            access_code=order.access_code,
            customer_name=sample["team_name"],
        )
        _append_sample_design(order, "Jersey", sample["qty_jrsy"])
        _append_sample_design(order, "Celana", sample["qty_cln"])
        db.session.add(order)
        created.append(so_number)

    db.session.commit()
    return {"created": created, "existing": existing}


def validate_vendor(vendor):
    vendor = str(vendor or "").strip()
    if vendor not in PRODUCTION_VENDORS:
        raise ValueError("Vendor produksi tidak valid.")
    return vendor


def production_status(order):
    return normalize_production_status(order.production_status)


def effective_deadline(order):
    return order.production_vendor_deadline or order.deadline


def production_priority(order, today=None):
    today = today or datetime.utcnow().date()
    deadline = effective_deadline(order)
    if not deadline or production_status(order) == "Finish":
        return "Normal"
    days_left = (deadline - today).days
    if days_left <= 0:
        return "Urgent"
    if days_left <= 3:
        return "Tinggi"
    return "Normal"


def is_late(order, today=None):
    today = today or datetime.utcnow().date()
    deadline = effective_deadline(order)
    return bool(deadline and deadline < today and production_status(order) != "Finish")


def assign_vendor(order, vendor):
    vendor = validate_vendor(vendor)
    order.production_vendor = vendor
    order.production_assigned_at = datetime.utcnow()
    if order.production_vendor_deadline:
        _advance_stage(order, "Jahit")
    db.session.commit()
    return order


def set_vendor_deadline(order, deadline):
    order.production_vendor_deadline = _parse_date(deadline)
    if order.production_vendor and order.production_vendor_deadline:
        _advance_stage(order, "Jahit")
    db.session.commit()
    return order


def can_finish_order(order):
    return production_status(order) == "Packing" or final_packing_checklist_complete(order)


def finish_production(order):
    if not can_finish_order(order):
        raise ValueError("Finish hanya bisa dilakukan jika status sudah Packing atau checklist packing sudah selesai.")
    _set_stage(order, "Finish")
    db.session.commit()
    return order


def final_packing_checklist_complete(order):
    players = _order_players(order)
    if not players:
        return False
    return all(player.checklist and player.checklist.qc_done for player in players)


def _parse_date(value):
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Deadline vendor tidak valid.") from exc


def _matches_search(order, search_value):
    values = [
        order.so_number,
        order.team_name,
        order.brand.name if order.brand else "",
        order.brand.code if order.brand else "",
        order.production_vendor,
        production_status(order),
        production_priority(order),
    ]
    return any(search_value in str(value or "").casefold() for value in values)


def list_vendor_production_rows(active_only=False):
    orders = (
        SalesOrder.query.filter_by(is_deleted=False, approval_status="approved")
        .all()
    )
    if active_only:
        orders = [order for order in orders if production_status(order) not in {"Finish", "Selesai"}]
    orders = sorted(
        orders,
        key=lambda order: (
            effective_deadline(order) or date.max,
            order.approved_at or order.created_at or datetime.min,
            order.id or 0,
        ),
    )
    return [
        {
            "so_number": order.so_number,
            "team_name": order.team_name,
            "brand": order.brand.code if order.brand else "-",
            "vendor": order.production_vendor or "-",
            "setting_by": order.setting_by_name or _setting_by_name(order),
            "status": production_status(order),
            "deadline_customer": order.deadline,
            "deadline_vendor": order.production_vendor_deadline,
            "production_in_at": order.production_assigned_at or order.approved_at or order.created_at,
        }
        for order in orders
    ]


def _include_in_vendor_print(order):
    status = production_status(order)
    if status in VENDOR_PRINT_EXCLUDED_STATUSES:
        return False
    if status in VENDOR_RETURNED_STATUSES:
        return bool(order.shortage_note)
    return True


def _set_stage(order, status):
    order.production_status = production_status(type("OrderStatus", (), {"production_status": status})())
    order.customer_portal_status = order.production_status
    order.production_status_updated_at = datetime.utcnow()
    if order.production_status == "Finish" and not order.tanggal_finish_produksi:
        order.tanggal_finish_produksi = order.production_status_updated_at


def _advance_stage(order, status):
    current_index = _status_index(production_status(order))
    next_status = production_status(type("OrderStatus", (), {"production_status": status})())
    if _status_index(next_status) >= current_index:
        _set_stage(order, next_status)


def _status_index(status):
    try:
        return PRODUCTION_STATUSES.index(status)
    except ValueError:
        return 0


def _vendor_print_row(order):
    return {
        "team_name": order.team_name,
        "status": order.production_status or production_status(order),
        "brand": order.brand.code if order.brand else "-",
        "qty": _order_qty_by_component(order),
        "assigned_at": order.production_assigned_at,
        "deadline": order.production_vendor_deadline,
        "shortage_note": vendor_shortage_note(order),
    }


def vendor_print_quantity_columns(rows):
    preferred = ["Celana", "Jersey"]
    seen = []
    for row in rows:
        for component, qty in row["qty"].items():
            if qty and component not in seen:
                seen.append(component)
    ordered = [component for component in preferred if component in seen]
    ordered.extend(component for component in seen if component not in ordered)
    return ordered


def _order_qty_by_component(order):
    qty = {}
    for design in order.designs:
        for component in design_components(design):
            qty[component] = qty.get(component, 0) + design.total_size
    return qty


def _order_players(order):
    return [
        player
        for design in sorted(order.designs, key=lambda row: (row.sort_order, row.id or 0))
        for player in sort_players_by_size(design.players)
    ]


def _setting_by_name(order):
    for player in _order_players(order):
        checklist = player.checklist
        if checklist and (checklist.setting_done_by_name or checklist.setting_user):
            return checklist.setting_done_by_name or checklist.setting_user.name
    return "-"


def _player_has_item(player, keyword):
    return any(component_key(component) == component_key(keyword) for component in design_components(player.design))


def _player_group_key(player):
    return (
        str(player.player_name or "").strip().casefold(),
        str(player.player_number or "").strip().casefold(),
        str(player.size or "").strip().casefold(),
    )


def vendor_shortage_note(order):
    parts = [value for value in [order.shortage_note, order.qc_note] if value]
    return " - ".join(parts) if parts else "-"


def _checklist_qc_data(checklist):
    if not checklist:
        return {}
    if checklist.qc_data:
        try:
            return json.loads(checklist.qc_data)
        except (TypeError, ValueError):
            return {}
    return {
        "jersey": bool(checklist.qc_jersey),
        "celana": bool(checklist.qc_celana),
    }


def _get_or_create_sample_brand(code, name):
    brand = Brand.query.filter_by(code=code).first()
    if brand:
        return brand
    brand = Brand(code=code, name=name, color="#c5162e", point_per_size=1, status="active")
    db.session.add(brand)
    db.session.flush()
    return brand


def _append_sample_design(order, item_name, qty):
    if qty <= 0:
        return
    design = SalesOrderDesign(
        design_name=item_name,
        item_name=item_name,
        material=order.material,
        pattern=order.pattern,
        grade=order.grade,
        production_days=order.production_days,
        deadline=order.deadline,
        instruction=order.instructions,
        sort_order=len(order.designs) + 1,
    )
    for index in range(1, qty + 1):
        design.players.append(
            SalesOrderPlayer(
                player_name=f"PLAYER {index:02d}",
                player_number=str(index),
                size="L",
                notes="-",
                sort_order=index,
            )
        )
    order.designs.append(design)


def _available_sample_so_number(requested_so_number):
    if not SalesOrder.query.filter_by(so_number=requested_so_number).first():
        return requested_so_number

    prefix, number = requested_so_number.rsplit("/", 1)
    next_number = int(number)
    while True:
        next_number += 1
        candidate = f"{prefix}/{next_number:04d}"
        if not SalesOrder.query.filter_by(so_number=candidate).first():
            return candidate
