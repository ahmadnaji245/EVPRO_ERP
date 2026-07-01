from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from database.db import db
from models import Brand, ProductionSizeChecklist, SalesOrderPlayer
from models.master_data import MasterInstruction, MasterItem, MasterMaterial, MasterPattern
from services.history_service import record_history
from services.brand_service import list_active_brands
from services.master_data_service import list_active_rows
from services.nota_service import billing_status_for_sales_order, get_nota_by_so_id
from services.pdf_service import build_sales_order_pdf
from services.sales_order_service import (
    PRODUCTION_STATUSES,
    create_sales_order,
    delete_sales_order,
    ensure_player_checklist,
    get_sales_order,
    list_sales_orders,
    update_production_status,
    update_sales_order,
    validate_sales_order_form,
)
from utils.constants import user_is_admin


sales_orders_bp = Blueprint("sales_orders", __name__, url_prefix="/sales-order")
sales_orders_approval_bp = Blueprint("sales_orders_approval", __name__, url_prefix="/sales-orders")


def _admin_required():
    if not user_is_admin(current_user):
        abort(403)


@sales_orders_bp.route("/")
@login_required
def index():
    sales_orders = list_sales_orders()
    billing_statuses = {order.id: billing_status_for_sales_order(order) for order in sales_orders}
    return render_template("so/index.html", sales_orders=sales_orders, billing_statuses=billing_statuses)


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
@login_required
def create():
    _admin_required()
    if request.method == "POST":
        errors = validate_sales_order_form(request.form)
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("so/create.html", **_form_context(form=request.form))
        order = create_sales_order(request.form, current_user, request.files)
        flash(f"Sales Order {order.so_number} berhasil dibuat.", "success")
        return redirect(url_for("sales_orders.detail", sales_order_id=order.id))
    return render_template("so/create.html", **_form_context(form={}))


@sales_orders_bp.route("/<int:sales_order_id>")
@login_required
def detail(sales_order_id):
    sales_order = get_sales_order(sales_order_id)
    return render_template(
        "so/detail.html",
        production_statuses=PRODUCTION_STATUSES,
        sales_order=sales_order,
        linked_nota=get_nota_by_so_id(sales_order.id),
        billing_status=billing_status_for_sales_order(sales_order),
    )


@sales_orders_approval_bp.route("/<int:sales_order_id>/approve-admin", methods=["POST"])
@login_required
def approve_admin(sales_order_id):
    _admin_required()
    order = get_sales_order(sales_order_id)
    if not order.approved:
        order.approved = True
        order.approved_by = "Admin"
        order.approved_source = "admin"
        order.approved_at = datetime.utcnow()
        record_history(
            order,
            actor_name="Admin",
            action="Approve Sales Order by Admin",
            field_name="approval_status",
            old_value="pending",
            new_value="approved",
            user=current_user,
        )
        db.session.commit()
        flash("Sales Order berhasil di-approve Admin.", "success")
    return redirect(url_for("sales_orders.detail", sales_order_id=order.id))


@sales_orders_bp.route("/<int:sales_order_id>/edit", methods=["GET", "POST"])
@login_required
def edit(sales_order_id):
    _admin_required()
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
        flash(f"Sales Order {order.so_number} berhasil diperbarui.", "success")
        return redirect(url_for("sales_orders.detail", sales_order_id=order.id))
    return render_template("so/edit.html", **_form_context(sales_order=order, form={}, revision_reason_admin=revision_reason_admin))


@sales_orders_bp.route("/<int:sales_order_id>/delete", methods=["POST"])
@login_required
def delete(sales_order_id):
    _admin_required()
    order = get_sales_order(sales_order_id)
    delete_sales_order(order)
    flash(f"Sales Order {order.so_number} dihapus.", "success")
    return redirect(url_for("sales_orders.index"))


@sales_orders_bp.route("/<int:sales_order_id>/print")
@login_required
def print_view(sales_order_id):
    _admin_required()
    return render_template("so/print.html", sales_order=get_sales_order(sales_order_id))


@sales_orders_bp.route("/<int:sales_order_id>/pdf")
@login_required
def pdf(sales_order_id):
    _admin_required()
    order = get_sales_order(sales_order_id)
    pdf_buffer = build_sales_order_pdf(order)
    filename = f"{order.so_number.replace('/', '-')}.pdf"
    response = send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=filename,
    )
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


@sales_orders_bp.route("/<int:sales_order_id>/production-status", methods=["POST"])
@login_required
def update_status(sales_order_id):
    order = get_sales_order(sales_order_id)
    try:
        update_production_status(order, request.form.get("production_status"))
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Status produksi diperbarui.", "success")
    return redirect(url_for("sales_orders.detail", sales_order_id=order.id))


@sales_orders_bp.route("/<int:sales_order_id>/production-checklist", methods=["POST"])
@login_required
def update_production_checklist(sales_order_id):
    order = get_sales_order(sales_order_id)
    player_ids = [player.id for design in order.designs for player in design.players]
    requested_setting = set(request.form.getlist("setting_done"))
    requested_size_setting = set(request.form.getlist("size_setting_done"))
    requested_qc = set(request.form.getlist("qc_done"))
    now = datetime.utcnow()
    current_user_name = current_user.name or current_user.username

    for player_id in player_ids:
        player = SalesOrderPlayer.query.get(player_id)
        checklist = ensure_player_checklist(player)
        setting_done = str(player_id) in requested_setting
        qc_done = str(player_id) in requested_qc
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

    db.session.commit()
    flash("Checklist produksi diperbarui.", "success")
    return redirect(url_for("sales_orders.detail", sales_order_id=order.id))
