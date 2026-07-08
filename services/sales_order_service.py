from datetime import datetime, time, timedelta

from database.db import db
from models import Brand, CustomerAccess, ProductionChecklist, SalesOrder, SalesOrderDesign, SalesOrderPlayer
from models.master_data import MasterInstruction
from services.history_service import record_history
from services.number_generator import generate_access_code, generate_customer_code, generate_so_number
from services.upload_service import save_upload
from utils.constants import PRODUCTION_STATUSES, normalize_production_status


VALID_PLAYER_SIZES = [
    "XS Kids",
    "S Kids",
    "M Kids",
    "L Kids",
    "XL Kids",
    "XXL Kids",
    "XS Women",
    "S Women",
    "M Women",
    "L Women",
    "XL Women",
    "XXL Women",
    "3XL Women",
    "S",
    "M",
    "L",
    "XL",
    "XXL",
    "3XL",
    "4XL",
    "5XL",
    "S Kids Lengan Panjang",
    "L Women Lengan Panjang",
    "XL Lengan Panjang",
    "L Lengan Panjang",
]
PLAYER_SIZE_LOOKUP = {size.casefold(): size for size in VALID_PLAYER_SIZES}


def _brand_is_evpro(brand):
    return bool(
        brand
        and (
            str(brand.name or "").strip().casefold() == "evpro"
            or str(brand.code or "").strip().casefold() == "evpro"
        )
    )


def _parse_date(value):
    value = str(value or "").strip()
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_int(value, default=7):
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _normalize_player_size(value):
    compact_value = " ".join(str(value or "").split())
    return PLAYER_SIZE_LOOKUP.get(compact_value.casefold())


def _is_player_number(value):
    return str(value or "").strip().isdigit()


def _parse_player_line(line, line_number):
    parts = [part.strip() for part in line.split(",")]
    if not parts or not parts[0]:
        raise ValueError(f"Baris player {line_number}: Size wajib diisi.")

    player_name = "-"
    player_number = "-"
    size = None
    notes = "-"

    if len(parts) == 1:
        size = _normalize_player_size(parts[0])
    elif len(parts) == 2:
        first_size = _normalize_player_size(parts[0])
        second_size = _normalize_player_size(parts[1])
        if first_size:
            size = first_size
            notes = parts[1] or "-"
        elif second_size:
            size = second_size
            if _is_player_number(parts[0]):
                player_number = parts[0] or "-"
            else:
                player_name = parts[0] or "-"
    elif len(parts) == 3:
        second_size = _normalize_player_size(parts[1])
        third_size = _normalize_player_size(parts[2])
        if second_size:
            player_name = parts[0] or "-"
            size = second_size
            notes = parts[2] or "-"
        elif third_size:
            player_name = parts[0] or "-"
            player_number = parts[1] or "-"
            size = third_size
    else:
        size = _normalize_player_size(parts[2])
        if size:
            player_name = parts[0] or "-"
            player_number = parts[1] or "-"
            notes = ", ".join(parts[3:]).strip() or "-"

    if not size:
        raise ValueError(f"Baris player {line_number}: Size tidak dikenali.")

    return SalesOrderPlayer(
        player_name=player_name,
        player_number=player_number,
        size=size,
        notes=notes,
        sort_order=line_number,
    )


def _parse_players(raw_players):
    players = []
    for index, line in enumerate(str(raw_players or "").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        players.append(_parse_player_line(line, index))
    return players


def _validate_players(raw_players, design_index):
    errors = []
    for line_number, line in enumerate(str(raw_players or "").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            _parse_player_line(line, line_number)
        except ValueError as exc:
            errors.append(f"Desain {design_index}, {exc}")
    return errors


def _get_list(form, key, fallback_key=None):
    values = form.getlist(key)
    if not values and fallback_key:
        value = form.get(fallback_key)
        values = [value] if value is not None else []
    return values


def _order_date(form, order=None):
    parsed = _parse_date(form.get("order_date"))
    if parsed:
        return parsed
    if order and order.created_at:
        return order.created_at.date()
    return datetime.utcnow().date()


def _fill_sales_order(order, form):
    brand = Brand.query.get(int(form.get("brand_id")))
    order_date = _order_date(form, order)
    order.team_name = form.get("team_name", "").strip()
    order.brand_id = brand.id
    order.seller_name = form.get("seller_name", "").strip() if _brand_is_evpro(brand) else None
    order.customer_code = form.get("customer_code", "").strip() or generate_customer_code(brand.code)
    order.material = form.get("material", "").strip() or None
    order.pattern = form.get("pattern", "").strip() or None
    order.grade = form.get("grade", "").strip() or None
    order.production_days = _parse_int(form.get("production_days"))
    order.deadline = order_date + timedelta(days=order.production_days)
    order.created_at = datetime.combine(order_date, time.min)
    order.instructions = form.get("instructions", "").strip() or None
    order.notes = form.get("notes", "").strip() or None
    return brand


def _sync_designs(order, form, files=None):
    design_ids = _get_list(form, "design_id[]")
    design_names = _get_list(form, "design_name[]", "design_name")
    item_names = _get_list(form, "item_name[]", "item_name")
    top_notes = _get_list(form, "top_notes[]", "design_instruction")
    bottom_notes = _get_list(form, "bottom_notes[]")
    players_list = _get_list(form, "players[]", "players")
    existing_top_images = _get_list(form, "existing_top_image[]", "existing_image[]")
    existing_bottom_images = _get_list(form, "existing_bottom_image[]")
    top_image_files = files.getlist("top_image[]") if files else []
    if not top_image_files and files:
        top_image_files = files.getlist("design_image[]")
    bottom_image_files = files.getlist("bottom_image[]") if files else []
    existing_designs = {str(design.id): design for design in order.designs}
    kept_designs = []

    for index, raw_name in enumerate(design_names):
        design_name = (raw_name or "").strip()
        if not design_name:
            continue

        design_id = design_ids[index] if index < len(design_ids) else ""
        design = existing_designs.get(str(design_id)) or SalesOrderDesign()
        design.design_name = design_name
        design.item_name = (item_names[index] if index < len(item_names) else "").strip() or "Jersey"
        design.material = order.material
        design.pattern = order.pattern
        design.grade = order.grade
        design.production_days = order.production_days
        design.deadline = order.deadline
        design.top_notes = (top_notes[index] if index < len(top_notes) else "").strip() or None
        design.bottom_notes = (bottom_notes[index] if index < len(bottom_notes) else "").strip() or None
        design.instruction = design.top_notes
        design.notes = None
        design.sort_order = index + 1

        top_image_file = top_image_files[index] if index < len(top_image_files) else None
        uploaded_top_path = save_upload(top_image_file, "designs") if top_image_file and top_image_file.filename else None
        if uploaded_top_path:
            design.top_image_path = uploaded_top_path
            design.image_path = uploaded_top_path
        elif not design.top_image_path and index < len(existing_top_images):
            design.top_image_path = existing_top_images[index] or design.image_path or None
            design.image_path = design.top_image_path

        bottom_image_file = bottom_image_files[index] if index < len(bottom_image_files) else None
        uploaded_bottom_path = save_upload(bottom_image_file, "designs") if bottom_image_file and bottom_image_file.filename else None
        if uploaded_bottom_path:
            design.bottom_image_path = uploaded_bottom_path
        elif not design.bottom_image_path and index < len(existing_bottom_images):
            design.bottom_image_path = existing_bottom_images[index] or None

        design.players.clear()
        design.players = _parse_players(players_list[index] if index < len(players_list) else "")
        kept_designs.append(design)
        if design not in order.designs:
            order.designs.append(design)

    for design in list(order.designs):
        if design not in kept_designs:
            order.designs.remove(design)


def ensure_player_checklist(player):
    if not player.checklist:
        player.checklist = ProductionChecklist()
        db.session.add(player.checklist)
    return player.checklist


def list_sales_orders():
    return (
        SalesOrder.query.filter_by(is_deleted=False)
        .order_by(SalesOrder.created_at.desc(), SalesOrder.id.desc())
        .all()
    )


def get_sales_order(sales_order_id):
    return SalesOrder.query.filter_by(id=sales_order_id, is_deleted=False).first_or_404()


def validate_sales_order_form(form):
    errors = []
    if not form.get("team_name", "").strip():
        errors.append("Nama tim wajib diisi.")
    if not form.get("brand_id"):
        errors.append("Brand wajib dipilih.")
    else:
        try:
            brand_id = int(form.get("brand_id"))
        except (TypeError, ValueError):
            brand_id = None
        if not brand_id or not Brand.query.get(brand_id):
            errors.append("Brand tidak valid.")
        else:
            brand = Brand.query.get(brand_id)
            if _brand_is_evpro(brand) and not form.get("seller_name", "").strip():
                errors.append("Nama seller wajib diisi untuk brand Evpro.")
    instruction = form.get("instructions", "").strip()
    if not instruction:
        errors.append("Instruksi Khusus wajib dipilih.")
    elif not MasterInstruction.query.filter_by(name=instruction, status="active").first():
        errors.append("Instruksi Khusus tidak valid.")
    design_names = _get_list(form, "design_name[]", "design_name")
    players_list = _get_list(form, "players[]", "players")
    valid_designs = [name for name in design_names if str(name or "").strip()]
    if not valid_designs:
        errors.append("Minimal satu desain wajib diisi.")
    for index, name in enumerate(design_names, start=1):
        if not str(name or "").strip():
            continue
        players = players_list[index - 1] if index - 1 < len(players_list) else ""
        if not str(players or "").strip():
            errors.append(f"Minimal satu player wajib diisi untuk desain {index}.")
        else:
            errors.extend(_validate_players(players, index))
    return errors


def create_sales_order(form, user, files=None):
    order = SalesOrder(created_by_id=user.id if user else None, access_code="-", production_status="Approval Customer")
    brand = _fill_sales_order(order, form)
    order.so_number = generate_so_number(brand.code, order.created_at.date() if order.created_at else None)
    order.access_code = generate_access_code(brand.code)
    order.customer_portal_status = "Approval Customer"
    _sync_designs(order, form, files)
    order.customer_access = CustomerAccess(
        access_code=order.access_code,
        customer_name=form.get("customer_name", "").strip() or order.team_name,
        customer_phone=form.get("customer_phone", "").strip() or None,
    )
    db.session.add(order)
    db.session.commit()
    return order


def update_sales_order(order, form, files=None, user=None):
    was_approved = order.approved
    was_customer_approved = order.approved_source == "customer" and order.approved
    _fill_sales_order(order, form)
    _sync_designs(order, form, files)
    if was_approved:
        order.approved = False
        order.approved_by = None
        order.approved_source = None
        order.approved_at = None
        order.customer_portal_status = "Approval Customer"
        order.production_status = "Approval Customer"
        order.production_status_updated_at = datetime.utcnow()
        actor_name = user.name if user else "System"
        record_history(
            order,
            actor_name=actor_name,
            action="Approval Admin dibatalkan karena revisi SO",
            field_name="approval_status",
            old_value="approved",
            new_value="pending",
            user=user,
        )
    if was_customer_approved:
        reason = form.get("revision_reason_admin", "").strip() or "Sales Order diperbarui oleh admin."
        order.revision_reason_admin = reason
        order.revision_time = datetime.utcnow()
        order.revision_by_admin_id = user.id if user else None
        record_history(
            order,
            actor_name=user.name if user else "System",
            action="Desain diperbarui oleh admin setelah approval customer",
            field_name="customer_portal_status",
            old_value="Desain Disetujui",
            new_value="Approval Customer",
            user=user,
            notes=reason,
        )
    if order.customer_access:
        order.customer_access.customer_name = form.get("customer_name", "").strip() or order.team_name
        order.customer_access.customer_phone = form.get("customer_phone", "").strip() or None
    db.session.commit()
    return order


def update_production_status(order, production_status):
    production_status = normalize_production_status(production_status)
    if production_status not in PRODUCTION_STATUSES:
        raise ValueError("Status produksi tidak valid.")
    order.production_status = production_status
    order.production_status_updated_at = datetime.utcnow()
    db.session.commit()
    return order


def set_production_stage(order, status):
    order.production_status = normalize_production_status(status)
    order.customer_portal_status = order.production_status
    order.production_status_updated_at = datetime.utcnow()
    if order.production_status == "Finish" and not order.tanggal_finish_produksi:
        order.tanggal_finish_produksi = order.production_status_updated_at
    return order


def delete_sales_order(order):
    order.is_deleted = True
    order.deleted_at = datetime.utcnow()
    db.session.commit()
