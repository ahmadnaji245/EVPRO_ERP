from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from database.db import db
from models.master_data import MasterInstruction, MasterItem, MasterMaterial, MasterPattern
from models.setting import Setting
from models.user import User
from services.brand_service import create_brand, get_brand, list_brands, set_brand_active, update_brand
from services.dashboard_service import monthly_setting_point_progress
from services.master_data_service import create_row, get_row, list_rows, set_row_active, update_row, validate_master_form
from services.pdf_service import build_production_report_pdf
from services.production_service import list_production_orders
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
from utils.constants import USER_ROLES, normalize_user_role, user_is_admin


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


@production_bp.route("/", endpoint="index")
@login_required
def production_index():
    _admin_required()
    return render_template("production/index.html", sales_orders=list_production_orders())


@production_bp.route("/<int:sales_order_id>", endpoint="detail")
@login_required
def production_detail(sales_order_id):
    _admin_required()
    return render_template("production/detail.html", sales_order_id=sales_order_id)


@master_bp.before_request
@login_required
def require_admin():
    _admin_required()


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
@login_required
def reports_index():
    _admin_required()
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
@login_required
def reports_pdf():
    _admin_required()
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
@login_required
def settings_index():
    _admin_required()
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
