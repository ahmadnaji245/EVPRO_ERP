from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from database.db import db
from models.master_data import MasterInstruction, MasterItem, MasterMaterial, MasterPattern
from models.setting import Setting
from models.user import User
from services.brand_service import create_brand, get_brand, list_brands, set_brand_active, update_brand
from services.dashboard_service import monthly_setting_point_progress
from services.master_data_service import create_row, get_row, list_rows, set_row_active, update_row, validate_master_form
from services.pdf_service import build_order_production_list_pdf, build_production_report_pdf, build_vendor_production_table_pdf
from services.pdf_render_service import render_first_pdf_page_to_jpg
from models.sales_order import SalesOrder
from services.production_service import (
    PRODUCTION_STATUSES,
    PRODUCTION_VENDORS,
    assign_vendor,
    can_finish_order,
    finish_production,
    list_production_orders,
    list_vendor_production_rows,
    production_priority,
    production_status,
    production_summary,
    prepare_qc_checklists,
    qc_checklist_rows,
    qc_checklist_rows_from_form,
    save_qc_checklist,
    set_vendor_deadline,
    validate_vendor,
    vendor_print_rows,
    vendor_print_quantity_columns,
    vendor_summary,
)
from services.report_service import (
    MONTH_OPTIONS,
    brand_filter_options,
    filter_title_parts,
    period_summary,
    production_report,
    report_summary,
    year_filter_options,
)
from services.validation_service import validate_brand_form
from utils.constants import USER_ROLES, normalize_user_role, user_is_admin, user_is_produksi
from utils.permissions import has_permission, permission_required


production_bp = Blueprint("production", __name__, url_prefix="/production")
master_bp = Blueprint("master", __name__, url_prefix="/master")
reports_bp = Blueprint("reports", __name__, url_prefix="/reports")
settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


SIMPLE_MASTERS = {
    "items": {
        "model": MasterItem,
        "title": "Master Item",
        "label": "Item",
        "endpoint": "master.items",
        "examples": "Jersey, Celana, Kaos, Jaket, Rompi, Training, Polo",
    },
    "materials": {
        "model": MasterMaterial,
        "title": "Master Material",
        "label": "Material",
        "endpoint": "master.materials",
        "examples": "Milano, Dryfit, Serena, Paragon, Hyget, Rabbit, Smash, Emboss, Jaquard",
    },
    "patterns": {
        "model": MasterPattern,
        "title": "Master Pola",
        "label": "Pola",
        "endpoint": "master.patterns",
        "examples": "A, B, C",
    },
    "instructions": {
        "model": MasterInstruction,
        "title": "Master Instruksi",
        "label": "Instruksi",
        "endpoint": "master.instructions",
        "examples": "Langsung Jahit, Sablon Dulu, Bordir Dulu",
    },
}


def _admin_required():
    if not user_is_admin(current_user):
        abort(403)


def _production_access_required():
    if not (user_is_admin(current_user) or user_is_produksi(current_user)):
        abort(403)


def _get_production_order(sales_order_id):
    return SalesOrder.query.filter_by(id=sales_order_id, is_deleted=False, approval_status="approved").first_or_404()


@production_bp.route("/", endpoint="index")
@permission_required("production.view")
def production_index():
    search = request.args.get("q", "").strip()
    sales_orders = list_production_orders(search)
    return render_template(
        "production/index.html",
        sales_orders=sales_orders,
        search=search,
        vendors=PRODUCTION_VENDORS,
        summary=production_summary(sales_orders),
        production_status=production_status,
        production_priority=production_priority,
        status_badge_class=_status_badge_class,
        can_finish_order=can_finish_order,
    )


@production_bp.route("/vendors", endpoint="vendors")
@permission_required("production.view")
def production_vendors():
    rows = list_vendor_production_rows()
    return render_template(
        "production/orders.html",
        rows=rows,
        vendor_rows=vendor_summary(list_production_orders()),
        status_badge_class=_status_badge_class,
    )


@production_bp.route("/orders", endpoint="orders")
@permission_required("production.view")
def production_orders():
    _production_access_required()
    return redirect(url_for("production.vendors"))


@production_bp.route("/vendors/pdf", endpoint="vendors_pdf")
@permission_required("production.view")
def production_vendors_pdf():
    rows = list_vendor_production_rows(active_only=True)
    pdf_buffer = build_order_production_list_pdf(rows)
    filename = "list-produksi-vendor.pdf"
    response = send_file(pdf_buffer, mimetype="application/pdf", as_attachment=False, download_name=filename)
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


@production_bp.route("/orders/pdf", endpoint="orders_pdf")
@permission_required("production.view")
def production_orders_pdf():
    _production_access_required()
    return redirect(url_for("production.vendors_pdf"))


@production_bp.route("/<int:sales_order_id>", endpoint="detail")
@permission_required("production.view")
def production_detail(sales_order_id):
    order = _get_production_order(sales_order_id)
    return redirect(url_for("sales_orders.detail", sales_order_id=order.id))


@production_bp.route("/<int:sales_order_id>/assign-vendor", methods=["POST"], endpoint="assign_vendor")
@permission_required("production.manage")
def production_assign_vendor(sales_order_id):
    order = _get_production_order(sales_order_id)
    try:
        assign_vendor(order, request.form.get("production_vendor"))
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"{order.so_number} berhasil di-assign ke {order.production_vendor}.", "success")
    return redirect(url_for("production.index", q=request.form.get("q", "")))


@production_bp.route("/<int:sales_order_id>/deadline-vendor", methods=["POST"], endpoint="set_deadline")
@permission_required("production.manage")
def production_set_deadline(sales_order_id):
    order = _get_production_order(sales_order_id)
    try:
        set_vendor_deadline(order, request.form.get("production_vendor_deadline"))
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"Deadline vendor {order.so_number} diperbarui.", "success")
    return redirect(url_for("production.index", q=request.form.get("q", "")))


@production_bp.route("/<int:sales_order_id>/finish", methods=["POST"], endpoint="finish")
@permission_required("production.manage")
def production_finish(sales_order_id):
    order = _get_production_order(sales_order_id)
    try:
        finish_production(order)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"Produksi {order.so_number} selesai.", "success")
    return redirect(url_for("production.index", q=request.form.get("q", "")))


@production_bp.route("/<int:sales_order_id>/qc-checklist", methods=["GET", "POST"], endpoint="qc_checklist")
@permission_required("production.manage")
def production_qc_checklist(sales_order_id):
    order = _get_production_order(sales_order_id)
    if request.method == "POST":
        try:
            save_qc_checklist(order, request.form)
        except ValueError as exc:
            flash(str(exc), "danger")
            qc_rows, qc_components = qc_checklist_rows_from_form(order, request.form)
            return render_template("production/qc_checklist.html", sales_order=order, qc_rows=qc_rows, qc_components=qc_components, form=request.form)
        flash("Checklist QC berhasil disimpan.", "success")
        return redirect(url_for("production.qc_checklist", sales_order_id=order.id))
    prepare_qc_checklists(order)
    qc_rows, qc_components = qc_checklist_rows(order)
    return render_template("production/qc_checklist.html", sales_order=order, qc_rows=qc_rows, qc_components=qc_components, form={})


@production_bp.route("/vendor/<path:vendor_name>/print", endpoint="vendor_print")
@permission_required("production.view")
def production_vendor_print(vendor_name):
    try:
        vendor = validate_vendor(vendor_name)
    except ValueError:
        abort(404)
    pdf_buffer = _build_vendor_print_pdf(vendor)
    filename = f"daftar-produksi-vendor-{vendor.casefold().replace(' ', '-')}.pdf"
    response = send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=filename,
    )
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


@production_bp.route("/vendor/<path:vendor_name>/print.jpg", endpoint="vendor_print_jpg")
@permission_required("production.view")
def production_vendor_print_jpg(vendor_name):
    try:
        vendor = validate_vendor(vendor_name)
    except ValueError:
        abort(404)
    pdf_buffer = _build_vendor_print_pdf(vendor)
    jpg_buffer = render_first_pdf_page_to_jpg(pdf_buffer)
    filename = f"vendor_{vendor.casefold().replace(' ', '_')}_{datetime.utcnow().date().isoformat()}.jpg"
    return send_file(
        jpg_buffer,
        mimetype="image/jpeg",
        as_attachment=True,
        download_name=filename,
    )


def _build_vendor_print_pdf(vendor):
    today = datetime.utcnow().date()
    rows = vendor_print_rows(vendor)
    quantity_columns = vendor_print_quantity_columns(rows)
    return build_vendor_production_table_pdf(
        vendor=vendor,
        rows=rows,
        quantity_columns=quantity_columns,
        printed_at=datetime.utcnow(),
        deadline_class=lambda deadline: _vendor_deadline_class(deadline, today),
    )


def _vendor_deadline_class(deadline, today):
    if not deadline:
        return ""
    days_left = (deadline - today).days
    if days_left < 0:
        return "deadline-late"
    if days_left == 1:
        return "deadline-h1"
    if days_left == 2:
        return "deadline-h2"
    return ""


def _status_badge_class(status):
    classes = {
        "Approval Customer": "text-bg-danger",
        "Setting": "text-bg-warning",
        "Printing": "text-bg-info",
        "Jahit": "text-bg-primary",
        "QC": "text-bg-secondary",
        "Packing": "text-bg-success",
        "Finish": "text-bg-success",
    }
    return classes.get(status, "text-bg-light")


@master_bp.before_request
@login_required
def require_admin():
    if not has_permission("master.view"):
        abort(403)


@master_bp.route("/", endpoint="index")
def master_index():
    return render_template(
        "master/index.html",
        brands=list_brands(),
        items=list_rows(MasterItem),
        materials=list_rows(MasterMaterial),
        patterns=list_rows(MasterPattern),
        instructions=list_rows(MasterInstruction),
        users=User.query.order_by(User.name).all(),
    )


@master_bp.route("/brands", methods=["GET", "POST"])
def brands():
    if request.method == "POST":
        errors = validate_brand_form(request.form)
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            create_brand(request.form, request.files.get("logo"))
            flash("Brand berhasil ditambahkan.", "success")
        return redirect(url_for("master.brands"))
    return render_template("master/brands.html", brands=list_brands(), editing_brand=None)


@master_bp.route("/brands/<int:brand_id>/edit", methods=["GET", "POST"])
def edit_brand(brand_id):
    brand = get_brand(brand_id)
    if request.method == "POST":
        errors = validate_brand_form(request.form, brand)
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            update_brand(brand, request.form, request.files.get("logo"))
            flash("Brand berhasil diperbarui.", "success")
            return redirect(url_for("master.brands"))
    return render_template("master/brands.html", brands=list_brands(), editing_brand=brand)


@master_bp.route("/brands/<int:brand_id>/deactivate", methods=["POST"])
def deactivate_brand(brand_id):
    set_brand_active(get_brand(brand_id), False)
    flash("Brand dinonaktifkan.", "success")
    return redirect(url_for("master.brands"))


@master_bp.route("/brands/<int:brand_id>/activate", methods=["POST"])
def activate_brand(brand_id):
    set_brand_active(get_brand(brand_id), True)
    flash("Brand diaktifkan kembali.", "success")
    return redirect(url_for("master.brands"))


def _simple_master_config(key):
    return SIMPLE_MASTERS[key]


def _render_simple_master(key, editing_row=None):
    config = _simple_master_config(key)
    return render_template(
        "master/simple_master_page.html",
        rows=list_rows(config["model"]),
        editing_row=editing_row,
        master_key=key,
        **config,
    )


def _create_simple_master(key):
    config = _simple_master_config(key)
    errors = validate_master_form(request.form, model=config["model"])
    if errors:
        for error in errors:
            flash(error, "danger")
    else:
        create_row(config["model"], request.form)
        flash(f"{config['label']} berhasil ditambahkan.", "success")
    return redirect(url_for(config["endpoint"]))


@master_bp.route("/items", methods=["GET", "POST"])
def items():
    if request.method == "POST":
        return _create_simple_master("items")
    return _render_simple_master("items")


@master_bp.route("/materials", methods=["GET", "POST"])
def materials():
    if request.method == "POST":
        return _create_simple_master("materials")
    return _render_simple_master("materials")


@master_bp.route("/patterns", methods=["GET", "POST"])
def patterns():
    if request.method == "POST":
        return _create_simple_master("patterns")
    return _render_simple_master("patterns")


@master_bp.route("/instructions", methods=["GET", "POST"])
def instructions():
    if request.method == "POST":
        return _create_simple_master("instructions")
    return _render_simple_master("instructions")


@master_bp.route("/<master_key>/<int:row_id>/edit", methods=["GET", "POST"])
def edit_simple_master(master_key, row_id):
    if master_key not in SIMPLE_MASTERS:
        return redirect(url_for("master.index"))
    config = _simple_master_config(master_key)
    row = get_row(config["model"], row_id)
    if request.method == "POST":
        errors = validate_master_form(request.form, model=config["model"], row=row)
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            update_row(row, request.form)
            flash(f"{config['label']} berhasil diperbarui.", "success")
            return redirect(url_for(config["endpoint"]))
    return _render_simple_master(master_key, editing_row=row)


@master_bp.route("/<master_key>/<int:row_id>/deactivate", methods=["POST"])
def deactivate_simple_master(master_key, row_id):
    if master_key not in SIMPLE_MASTERS:
        return redirect(url_for("master.index"))
    config = _simple_master_config(master_key)
    set_row_active(get_row(config["model"], row_id), False)
    flash(f"{config['label']} dinonaktifkan.", "success")
    return redirect(url_for(config["endpoint"]))


@master_bp.route("/<master_key>/<int:row_id>/activate", methods=["POST"])
def activate_simple_master(master_key, row_id):
    if master_key not in SIMPLE_MASTERS:
        return redirect(url_for("master.index"))
    config = _simple_master_config(master_key)
    set_row_active(get_row(config["model"], row_id), True)
    flash(f"{config['label']} diaktifkan kembali.", "success")
    return redirect(url_for(config["endpoint"]))


@master_bp.route("/users", methods=["GET", "POST"])
def users():
    if request.method == "POST":
        errors = _validate_user_form(request.form)
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            user = User(
                name=request.form.get("name", "").strip(),
                username=request.form.get("username", "").strip(),
                role=normalize_user_role(request.form.get("role", "produksi")),
                is_active=request.form.get("is_active", "1") == "1",
            )
            user.set_password(request.form.get("password") or "password123")
            db.session.add(user)
            db.session.commit()
            flash("User berhasil ditambahkan.", "success")
        return redirect(url_for("master.users"))
    return render_template("master/users.html", users=User.query.order_by(User.name).all(), roles=USER_ROLES, editing_user=None)


@master_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        errors = _validate_user_form(request.form, user)
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            user.name = request.form.get("name", "").strip()
            user.username = request.form.get("username", "").strip()
            user.role = normalize_user_role(request.form.get("role", user.role))
            user.is_active = request.form.get("is_active", "1") == "1"
            if request.form.get("password"):
                user.set_password(request.form.get("password"))
            db.session.commit()
            flash("User berhasil diperbarui.", "success")
            return redirect(url_for("master.users"))
    return render_template("master/users.html", users=User.query.order_by(User.name).all(), roles=USER_ROLES, editing_user=user)


@master_bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    flash("User dinonaktifkan.", "success")
    return redirect(url_for("master.users"))


@master_bp.route("/users/<int:user_id>/activate", methods=["POST"])
def activate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = True
    db.session.commit()
    flash("User diaktifkan kembali.", "success")
    return redirect(url_for("master.users"))


@reports_bp.route("/", endpoint="index")
@permission_required("reports.view")
def reports_index():
    selected_brand = request.args.get("brand", "").strip()
    selected_month = request.args.get("month", "").strip()
    selected_year = request.args.get("year", "").strip()
    report = production_report(selected_brand, selected_month, selected_year)
    return render_template(
        "reports/index.html",
        brand_options=brand_filter_options(),
        month_options=MONTH_OPTIONS,
        year_options=year_filter_options(),
        selected_brand=selected_brand,
        selected_month=selected_month,
        selected_year=selected_year,
        summary=report_summary(selected_brand, selected_month, selected_year),
        period_summary=period_summary(report),
        report=report,
    )


@reports_bp.route("/pdf", endpoint="pdf")
@permission_required("reports.view")
def reports_pdf():
    selected_brand = request.args.get("brand", "").strip()
    selected_month = request.args.get("month", "").strip()
    selected_year = request.args.get("year", "").strip()
    title_parts = filter_title_parts(selected_brand, selected_month, selected_year)
    title = "Laporan Sales Order Produksi"
    if title_parts:
        title = f"{title} - {' - '.join(title_parts)}"
    pdf_buffer = build_production_report_pdf(production_report(selected_brand, selected_month, selected_year), title=title)
    filename = "laporan-sales-order-produksi.pdf"
    response = send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=filename,
    )
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


@settings_bp.route("/", methods=["GET", "POST"], endpoint="index")
@permission_required("settings.view")
def settings_index():
    target = Setting.query.filter_by(key="monthly_target").first()
    if request.method == "POST":
        if not target:
            target = Setting(key="monthly_target")
            db.session.add(target)
        target.value = request.form.get("monthly_target", "0")
        db.session.commit()
        flash("Pengaturan berhasil disimpan.", "success")
        return redirect(url_for("settings.index"))
    return render_template("settings/index.html", target=target, setting_progress=monthly_setting_point_progress())


def _validate_user_form(form, user=None):
    errors = []
    name = form.get("name", "").strip()
    username = form.get("username", "").strip()
    if not name:
        errors.append("Nama user wajib diisi.")
    if not username:
        errors.append("Username wajib diisi.")
    if not user and not form.get("password"):
        errors.append("Password wajib diisi untuk user baru.")
    role = normalize_user_role(form.get("role"))
    if role not in USER_ROLES:
        errors.append("Role user tidak valid.")
    if username:
        query = User.query.filter_by(username=username)
        if user:
            query = query.filter(User.id != user.id)
        if query.first():
            errors.append("Username sudah digunakan.")
    return errors
