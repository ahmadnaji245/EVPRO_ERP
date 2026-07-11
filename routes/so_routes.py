from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from database.db import db
from models import Brand, ProductionSizeChecklist, SalesOrderPlayer
from models.master_data import MasterInstruction, MasterItem, MasterMaterial, MasterPattern
from services.history_service import record_history
from services.brand_service import list_active_brands
from services.crm_service import get_lead, lead_form_data_for_sales_order
from services.dashboard_service import dashboard_stats, monthly_point_chart, monthly_setting_point_progress
from services.master_data_service import list_active_rows
from services.nota_service import billing_status_for_sales_order, get_nota_by_so_id
from services.order_status_service import get_display_status
from services.pdf_service import build_sales_order_pdf
from services.production_photo_service import add_production_photos, delete_production_photo, get_photo_for_order
from services.sales_order_service import (
    PRODUCTION_STATUSES,
    create_sales_order,
    delete_sales_order,
    ensure_player_checklist,
    get_sales_order,
    list_sales_orders,
    set_production_stage,
    update_sales_order,
    validate_sales_order_form,
)
from utils.constants import user_is_admin, user_is_desain, user_is_produksi
from utils.helpers import sales_order_pdf_download_name
from utils.permissions import has_permission, permission_required


sales_orders_bp = Blueprint("sales_orders", __name__, url_prefix="/sales-order")
sales_orders_approval_bp = Blueprint("sales_orders_approval", __name__, url_prefix="/sales-orders")


def _admin_required():
    if not user_is_admin(current_user):
        abort(403)


def _production_or_admin_required():
    if not (user_is_admin(current_user) or user_is_produksi(current_user)):
        abort(403)


def _sales_order_access_required():
    if not (user_is_admin(current_user) or user_is_desain(current_user) or user_is_produksi(current_user)):
        abort(403)


@sales_orders_bp.route("/")
@permission_required("sales_order.view")
def index():
    search = request.args.get("q", "").strip()
    sales_orders = list_sales_orders()
    billing_statuses = {order.id: billing_status_for_sales_order(order) for order in sales_orders}
    display_statuses = {order.id: get_display_status(order) for order in sales_orders}

    if search:
        search_value = search.casefold()

        def matches_search(order):
            brand_name = order.brand.name if order.brand else ""
            brand_code = order.brand.code if order.brand else ""
            customer_name = order.customer_access.customer_name if order.customer_access else ""
            searchable_values = [
                order.so_number,
                brand_name,
                brand_code,
                customer_name,
                order.team_name,
                display_statuses.get(order.id, {}).get("status"),
                display_statuses.get(order.id, {}).get("list_status"),
                billing_statuses.get(order.id, "Belum Ada Nota"),
            ]
            return any(search_value in str(value or "").casefold() for value in searchable_values)

        sales_orders = [order for order in sales_orders if matches_search(order)]

    return render_template(
        "so/index.html",
        sales_orders=sales_orders,
        billing_statuses=billing_statuses,
        display_statuses=display_statuses,
        search=search,
    )


@sales_orders_bp.route("/dashboard")
@permission_required("sales_order.view")
def dashboard():
    return render_template(
        "so/dashboard.html",
        stats=dashboard_stats(),
        monthly=monthly_point_chart(),
        setting_progress=monthly_setting_point_progress(),
    )


def _form_context(**kwargs):
    sales_order = kwargs.get("sales_order")
    brands = list_active_brands()
    if sales_order and sales_order.brand and sales_order.brand not in brands:
        brands.append(sales_order.brand)
    context = {
        "brands": brands,
        "items": list_active_rows(MasterItem),
        "materials": list_active_rows(MasterMaterial),
        "patterns": list_active_rows(MasterPattern),
        "instructions": list_active_rows(MasterInstruction),
    }
    context.update(kwargs)
    return context


@sales_orders_bp.route("/create", methods=["GET", "POST"])
@permission_required("sales_order.manage")
def create():
    if request.method == "POST":
        errors = validate_sales_order_form(request.form)
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("so/create.html", **_form_context(form=request.form))
        order = create_sales_order(request.form, current_user, request.files)
        flash(f"Surat Order {order.so_number} berhasil dibuat.", "success")
        return redirect(url_for("sales_orders.detail", sales_order_id=order.id))
    lead_id = request.args.get("lead_id")
    if str(lead_id or "").isdigit():
        lead = get_lead(int(lead_id))
        return render_template("so/create.html", **_form_context(form=lead_form_data_for_sales_order(lead), source_lead=lead))
    return render_template("so/create.html", **_form_context(form={}, source_lead=None))


@sales_orders_bp.route("/<int:sales_order_id>")
@permission_required("sales_order.view")
def detail(sales_order_id):
    _sales_order_access_required()
    sales_order = get_sales_order(sales_order_id)
    return render_template(
        "so/detail.html",
        production_statuses=PRODUCTION_STATUSES,
        sales_order=sales_order,
        display_status=get_display_status(sales_order),
        linked_nota=get_nota_by_so_id(sales_order.id),
        billing_status=billing_status_for_sales_order(sales_order),
    )


@sales_orders_bp.route("/<int:sales_order_id>/production-photos", methods=["POST"])
@permission_required("sales_order.production_photo")
def upload_production_photos(sales_order_id):
    _production_or_admin_required()
    order = get_sales_order(sales_order_id)
    try:
        photos = add_production_photos(order, request.files.getlist("production_photos"), current_user)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        if photos:
            flash(f"{len(photos)} foto hasil produksi berhasil diupload.", "success")
        else:
            flash("Pilih minimal satu foto hasil produksi.", "warning")
    return redirect(url_for("sales_orders.detail", sales_order_id=order.id))


@sales_orders_bp.route("/<int:sales_order_id>/production-photos/<int:photo_id>/delete", methods=["POST"])
@permission_required("sales_order.production_photo")
def delete_production_photo_route(sales_order_id, photo_id):
    _production_or_admin_required()
    order = get_sales_order(sales_order_id)
    photo = get_photo_for_order(order, photo_id)
    delete_production_photo(photo)
    flash("Foto hasil produksi dihapus.", "success")
    return redirect(url_for("sales_orders.detail", sales_order_id=order.id))


@sales_orders_approval_bp.route("/<int:sales_order_id>/approve-admin", methods=["POST"])
@permission_required("sales_order.manage")
def approve_admin(sales_order_id):
    order = get_sales_order(sales_order_id)
    if not order.approved:
        order.approved = True
        order.approved_by = "Admin"
        order.approved_source = "admin"
        order.approved_at = datetime.utcnow()
        set_production_stage(order, "Setting")
        record_history(
            order,
            actor_name="Admin",
            action="Approve Surat Order by Admin",
            field_name="approval_status",
            old_value="pending",
            new_value="approved",
            user=current_user,
        )
        db.session.commit()
        flash("Sales Order berhasil di-approve Admin.", "success")
    return redirect(url_for("sales_orders.detail", sales_order_id=order.id))


@sales_orders_bp.route("/<int:sales_order_id>/edit", methods=["GET", "POST"])
@permission_required("sales_order.manage")
def edit(sales_order_id):
    order = get_sales_order(sales_order_id)
    revision_reason_admin = request.values.get("revision_reason_admin", "").strip()
    if order.approved_source == "customer" and order.approved and not revision_reason_admin:
        flash("Alasan perubahan wajib diisi karena desain sudah disetujui customer.", "danger")
        return redirect(url_for("sales_orders.detail", sales_order_id=order.id))
    if request.method == "POST":
        errors = validate_sales_order_form(request.form)
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("so/edit.html", **_form_context(sales_order=order, form=request.form, revision_reason_admin=revision_reason_admin))
        update_sales_order(order, request.form, request.files, current_user)
        flash(f"Surat Order {order.so_number} berhasil diperbarui.", "success")
        return redirect(url_for("sales_orders.detail", sales_order_id=order.id))
    return render_template("so/edit.html", **_form_context(sales_order=order, form={}, revision_reason_admin=revision_reason_admin))


@sales_orders_bp.route("/<int:sales_order_id>/delete", methods=["POST"])
@permission_required("sales_order.manage")
def delete(sales_order_id):
    order = get_sales_order(sales_order_id)
    if get_nota_by_so_id(order.id):
        flash("SO ini sudah memiliki Nota. Hapus Nota terlebih dahulu sebelum menghapus SO.", "warning")
        return redirect(url_for("sales_orders.index"))
    delete_sales_order(order)
    flash(f"Surat Order {order.so_number} dihapus.", "success")
    return redirect(url_for("sales_orders.index"))


@sales_orders_bp.route("/<int:sales_order_id>/print")
@permission_required("sales_order.manage")
def print_view(sales_order_id):
    return render_template("so/print.html", sales_order=get_sales_order(sales_order_id))


@sales_orders_bp.route("/<int:sales_order_id>/pdf")
@permission_required("sales_order.pdf")
def pdf(sales_order_id):
    order = get_sales_order(sales_order_id)
    pdf_buffer = build_sales_order_pdf(order)
    filename = sales_order_pdf_download_name(order)
    response = send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=filename,
    )
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


@sales_orders_bp.route("/<int:sales_order_id>/production-checklist", methods=["POST"])
@permission_required("sales_order.view")
def update_production_checklist(sales_order_id):
    _sales_order_access_required()
    can_update_setting = has_permission("sales_order.setting_checklist")
    can_update_checking = has_permission("production.update_checking")
    if not (can_update_setting or can_update_checking):
        abort(403)
    order = get_sales_order(sales_order_id)
    player_ids = [player.id for design in order.designs for player in design.players]
    requested_setting = set(request.form.getlist("setting_done")) if can_update_setting else set()
    requested_size_setting = set(request.form.getlist("size_setting_done")) if can_update_setting else set()
    requested_qc = set(request.form.getlist("qc_done")) if can_update_checking else set()
    now = datetime.utcnow()
    current_user_name = current_user.name or current_user.username

    for player_id in player_ids:
        player = SalesOrderPlayer.query.get(player_id)
        checklist = ensure_player_checklist(player)
        if can_update_setting:
            setting_done = str(player_id) in requested_setting
            setting_owner_id = checklist.setting_done_by_user_id or checklist.setting_user_id
            if checklist.setting_done:
                if not setting_done and setting_owner_id == current_user.id:
                    checklist.setting_done = False
                    checklist.setting_user_id = None
                    checklist.setting_at = None
                    checklist.setting_done_by_user_id = None
                    checklist.setting_done_by_name = None
                    checklist.setting_done_at = None
            elif setting_done:
                checklist.setting_done = setting_done
                checklist.setting_user_id = current_user.id
                checklist.setting_at = now
                checklist.setting_done_by_user_id = current_user.id
                checklist.setting_done_by_name = current_user_name
                checklist.setting_done_at = now

        if can_update_checking:
            qc_done = str(player_id) in requested_qc
            qc_owner_id = checklist.qc_done_by_user_id or checklist.qc_user_id
            if checklist.qc_done:
                if not qc_done and qc_owner_id == current_user.id:
                    checklist.qc_done = False
                    checklist.qc_user_id = None
                    checklist.qc_at = None
                    checklist.qc_done_by_user_id = None
                    checklist.qc_done_by_name = None
                    checklist.qc_done_at = None
            elif qc_done:
                checklist.qc_done = qc_done
                checklist.qc_user_id = current_user.id
                checklist.qc_at = now
                checklist.qc_done_by_user_id = current_user.id
                checklist.qc_done_by_name = current_user_name
                checklist.qc_done_at = now

    if can_update_setting:
        for design in order.designs:
            rows = []
            recap = design.size_recap
            for group_rows in recap["groups"].values():
                rows.extend(group_rows)
            rows.extend(recap["long_sleeve"])

            existing = {
                checklist.size: checklist
                for checklist in design.size_checklists
            }
            for row in rows:
                size = " ".join((row["size"] or "").split())
                key = f"{design.id}|{size}"
                checklist = existing.get(size)
                if not checklist:
                    checklist = ProductionSizeChecklist(design=design, size=size)
                    db.session.add(checklist)
                setting_done = key in requested_size_setting
                if checklist.setting_done != setting_done:
                    checklist.setting_done = setting_done
                    checklist.setting_user_id = current_user.id if setting_done else None
                    checklist.setting_at = now if setting_done else None

    if can_update_setting and order.approved and _setting_checklist_complete(order) and _production_stage_index(order.production_status_label) < _production_stage_index("Printing"):
        order.setting_by_name = current_user_name
        set_production_stage(order, "Printing")

    if can_update_checking and order.approved and _final_packing_checklist_complete(order):
        set_production_stage(order, "Finish")

    db.session.commit()
    flash("Checklist produksi diperbarui.", "success")
    return redirect(url_for("sales_orders.detail", sales_order_id=order.id))


def _setting_checklist_complete(order):
    players = [player for design in order.designs for player in design.players]
    if not players or not all(player.checklist and player.checklist.setting_done for player in players):
        return False
    for design in order.designs:
        rows = []
        recap = design.size_recap
        for group_rows in recap["groups"].values():
            rows.extend(group_rows)
        rows.extend(recap["long_sleeve"])
        if any(not design.size_setting_done(row["size"]) for row in rows):
            return False
    return True


def _final_packing_checklist_complete(order):
    players = [player for design in order.designs for player in design.players]
    return bool(players) and all(player.checklist and player.checklist.qc_done for player in players)


def _production_stage_index(status):
    try:
        return PRODUCTION_STATUSES.index(status)
    except ValueError:
        return 0
