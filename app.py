from pathlib import Path

from datetime import datetime
from flask import Blueprint, Flask, abort, current_app, flash, redirect, render_template, request, send_file, session, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from sqlalchemy import inspect, text

from config import Config
from database.db import db
from models import Brand, MasterInstruction, MasterItem, MasterMaterial, MasterPattern, SalesOrder, Setting, User
from routes.crm_routes import crm_bp
from routes.handover_routes import handover_bp
from routes.nota_routes import _pdf_invoice, _pdf_items, _pdf_payments, nota_bp
from routes.so_shell_routes import master_bp, production_bp, reports_bp, settings_bp
from routes.so_routes import sales_orders_approval_bp, sales_orders_bp
from services.nota_service import seed_default_nota_products
from services.crm_service import refresh_all_customer_stats, seed_default_whatsapp_templates, sync_nota_customer, sync_sales_order_customer
from services.customer_service import find_by_access_code
from services.history_service import record_history
from services.nota_service import calculate_invoice_status, display_nota_number, get_nota_by_so_id, totals
from services.order_status_service import get_display_status
from services.pdf_service import build_customer_sales_order_pdf
from services.production_photo_service import get_photo_for_order
from services.production_service import PRODUCTION_STATUSES, seed_production_sample_data
from services.nota_pdf_ff_apparel_service import build_ff_apparel_pdf
from services.nota_pdf_service import build_customer_invoice_pdf
from services.number_generator import generate_tracking_code
from services.sales_order_service import get_sales_order_by_tracking_code, set_production_stage
from utils.formatters import register_filters
from utils.helpers import active_class, ensure_upload_folders, nota_pdf_download_name, sales_order_pdf_download_name
from utils.permissions import has_permission, permission_required
from utils.constants import long_sleeve_size_label, long_sleeve_type_label, normalize_size_key, sort_long_sleeve_rows, sort_size_rows


login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
tracking_bp = Blueprint("tracking", __name__, url_prefix="/tracking")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@dashboard_bp.route("/")
@permission_required("dashboard.view")
def index():
    return render_template("dashboard.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    from flask import flash, request

    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index") if current_user.is_admin else url_for("sales_orders.index"))

    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username", "").strip()).first()
        if user and user.is_active and user.check_password(request.form.get("password", "")):
            login_user(user, remember=True)
            default_endpoint = "dashboard.index" if user.is_admin else "sales_orders.index"
            return redirect(request.args.get("next") or url_for(default_endpoint))
        flash("Username atau password tidak sesuai.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    from flask import flash

    logout_user()
    flash("Anda sudah logout.", "success")
    return redirect(url_for("auth.login"))


@tracking_bp.route("/<access_code>")
def detail(access_code):
    access_record = find_by_access_code(access_code)
    if not access_record or not access_record.sales_order or access_record.sales_order.is_deleted:
        return render_template(
            "so/customer.html",
            access_record=None,
            production_statuses=PRODUCTION_STATUSES,
            portal_progress=None,
            linked_nota=None,
            nota_totals=None,
            invoice_status=None,
            production_photos=[],
            portal_design_player_groups=[],
            portal_size_recap={},
            portal_long_sleeve_recap=[],
        ), 404
    order = access_record.sales_order
    linked_nota = get_nota_by_so_id(access_record.sales_order.id) if access_record else None
    return render_template(
        "so/customer.html",
        access_record=access_record,
        production_statuses=PRODUCTION_STATUSES,
        portal_progress=customer_portal_progress(order) if access_record else None,
        portal_order_status=customer_portal_order_status(order) if access_record else None,
        linked_nota=linked_nota,
        nota_totals=totals(linked_nota) if linked_nota else None,
        invoice_status=calculate_invoice_status(linked_nota) if linked_nota else None,
        production_photos=list(order.production_photos) if customer_can_view_production_photos(order) else [],
        can_view_production_photos=customer_can_view_production_photos(order),
        portal_design_player_groups=customer_portal_design_player_groups(order),
        portal_size_recap=customer_portal_size_recap(order),
        portal_long_sleeve_recap=customer_portal_long_sleeve_recap(order),
        public_tracking_code=None,
    )


def _render_tracking_detail(order, status_code=200):
    if not order or order.is_deleted or not order.customer_access:
        return render_template(
            "so/customer.html",
            access_record=None,
            production_statuses=PRODUCTION_STATUSES,
            portal_progress=None,
            linked_nota=None,
            nota_totals=None,
            invoice_status=None,
            production_photos=[],
            portal_design_player_groups=[],
            portal_size_recap={},
            portal_long_sleeve_recap=[],
            public_tracking_code=None,
        ), 404
    access_record = order.customer_access
    linked_nota = get_nota_by_so_id(order.id)
    return render_template(
        "so/customer.html",
        access_record=access_record,
        production_statuses=PRODUCTION_STATUSES,
        portal_progress=customer_portal_progress(order),
        portal_order_status=customer_portal_order_status(order),
        linked_nota=linked_nota,
        nota_totals=totals(linked_nota) if linked_nota else None,
        invoice_status=calculate_invoice_status(linked_nota) if linked_nota else None,
        production_photos=list(order.production_photos) if customer_can_view_production_photos(order) else [],
        can_view_production_photos=customer_can_view_production_photos(order),
        portal_design_player_groups=customer_portal_design_player_groups(order),
        portal_size_recap=customer_portal_size_recap(order),
        portal_long_sleeve_recap=customer_portal_long_sleeve_recap(order),
        public_tracking_code=order.tracking_code,
    ), status_code


@tracking_bp.route("", methods=["GET", "POST"])
@tracking_bp.route("/", methods=["GET", "POST"])
def lookup():
    tracking_code = request.form.get("tracking_code", "").strip().upper()
    if request.method == "POST":
        order = get_sales_order_by_tracking_code(tracking_code)
        if order:
            return redirect(url_for("public_tracking_detail", tracking_code=order.tracking_code))
        flash("Kode tracking tidak ditemukan.", "danger")
    return render_template("so/tracking_lookup.html", tracking_code=tracking_code)


@tracking_bp.route("/<access_code>/approve", methods=["POST"])
def approve_customer(access_code):
    access_record = find_by_access_code(access_code)
    if not access_record:
        abort(404)
    order = access_record.sales_order
    if not order.approved:
        old_status = order.approval_status
        order.approved = True
        order.approved_by = access_record.customer_name or order.team_name
        order.approved_source = "customer"
        order.approved_at = datetime.utcnow()
        set_production_stage(order, "Setting")
        record_history(
            order,
            actor_name=access_record.customer_name or "Customer",
            action="Surat Order disetujui customer",
            field_name="approval_status",
            old_value=old_status,
            new_value="approved",
            notes=f"Customer portal token: {access_record.access_code}",
        )
        db.session.commit()
        flash("Surat Order berhasil disetujui.", "success")
    return redirect(url_for("tracking.detail", access_code=access_code))


def approve_customer_order(order):
    access_record = order.customer_access if order else None
    if not access_record:
        abort(404)
    if not order.approved:
        old_status = order.approval_status
        order.approved = True
        order.approved_by = access_record.customer_name or order.team_name
        order.approved_source = "customer"
        order.approved_at = datetime.utcnow()
        set_production_stage(order, "Setting")
        record_history(
            order,
            actor_name=access_record.customer_name or "Customer",
            action="Surat Order disetujui customer",
            field_name="approval_status",
            old_value=old_status,
            new_value="approved",
            notes=f"Tracking code: {order.tracking_code}",
        )
        db.session.commit()
        flash("Surat Order berhasil disetujui.", "success")


@tracking_bp.route("/<access_code>/production-photos/<int:photo_id>")
def production_photo(access_code, photo_id):
    access_record = find_by_access_code(access_code)
    if not access_record or not access_record.sales_order or access_record.sales_order.is_deleted:
        abort(404)
    order = access_record.sales_order
    if not customer_can_view_production_photos(order):
        abort(404)
    photo = get_photo_for_order(order, photo_id)
    return _send_production_photo_file(photo, as_attachment=False)


@tracking_bp.route("/<access_code>/production-photos/<int:photo_id>/download")
def production_photo_download(access_code, photo_id):
    access_record = find_by_access_code(access_code)
    if not access_record or not access_record.sales_order or access_record.sales_order.is_deleted:
        abort(404)
    order = access_record.sales_order
    if not customer_can_view_production_photos(order):
        abort(404)
    photo = get_photo_for_order(order, photo_id)
    return _send_production_photo_file(photo, as_attachment=True)


@tracking_bp.route("/<access_code>/surat-order.pdf")
def sales_order_download(access_code):
    access_record = find_by_access_code(access_code)
    if not access_record or not access_record.sales_order or access_record.sales_order.is_deleted:
        abort(404)
    order = access_record.sales_order
    filename = sales_order_pdf_download_name(order)
    return send_file(
        build_customer_sales_order_pdf(order),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@tracking_bp.route("/<access_code>/nota.pdf")
def nota_download(access_code):
    access_record = find_by_access_code(access_code)
    if not access_record or not access_record.sales_order or access_record.sales_order.is_deleted:
        abort(404)
    nota = get_nota_by_so_id(access_record.sales_order.id)
    if not nota:
        abort(404)
    invoice = _pdf_invoice(nota, mapped_brand=True)
    if invoice["brand"] == "FF Apparel":
        pdf = build_ff_apparel_pdf(invoice, _pdf_items(nota), _pdf_payments(nota), totals(nota))
    else:
        pdf = build_customer_invoice_pdf(invoice, _pdf_items(nota), totals(nota))
    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=nota_pdf_download_name(nota),
    )


def _sales_order_download_for_order(order):
    if not order or order.is_deleted:
        abort(404)
    filename = sales_order_pdf_download_name(order)
    return send_file(
        build_customer_sales_order_pdf(order),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


def _nota_download_for_order(order):
    if not order or order.is_deleted:
        abort(404)
    nota = get_nota_by_so_id(order.id)
    if not nota:
        abort(404)
    invoice = _pdf_invoice(nota, mapped_brand=True)
    if invoice["brand"] == "FF Apparel":
        pdf = build_ff_apparel_pdf(invoice, _pdf_items(nota), _pdf_payments(nota), totals(nota))
    else:
        pdf = build_customer_invoice_pdf(invoice, _pdf_items(nota), totals(nota))
    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=nota_pdf_download_name(nota),
    )


def customer_portal_progress(order):
    players = [player for design in order.designs for player in design.players]
    player_total = len(players)
    setting_done = sum(1 for player in players if player.checklist and player.checklist.setting_done)
    packing_done = sum(1 for player in players if player.checklist and player.checklist.qc_done)
    size_rows = []
    size_done = 0
    for design in order.designs:
        recap = design.size_recap
        for group_rows in recap["groups"].values():
            size_rows.extend((design, row["size"]) for row in group_rows)
        size_rows.extend((design, row["size"]) for row in recap["long_sleeve"])
    for design, size in size_rows:
        if design.size_setting_done(size):
            size_done += 1
    size_total = len(size_rows)
    current_status = "Approval Customer" if not order.approved else order.production_status_label
    current_index = PRODUCTION_STATUSES.index(current_status) if current_status in PRODUCTION_STATUSES else 0
    return {
        "current_status": current_status,
        "current_index": current_index,
        "status_updated_at": order.production_status_updated_at or order.approved_at or order.created_at,
        "setting_done": setting_done,
        "setting_total": player_total,
        "size_setting_done": size_done,
        "size_setting_total": size_total,
        "packing_done": packing_done,
        "packing_total": player_total,
    }


def customer_portal_order_status(order):
    return get_display_status(order)


def customer_can_view_production_photos(order):
    if not order.approved:
        return False
    return order.production_status_label == "Finish" or bool(order.tanggal_finish_produksi)


def customer_portal_design_player_groups(order):
    groups = []
    for design_index, design in enumerate(sorted(order.designs, key=lambda item: (item.sort_order, item.id)), start=1):
        players = []
        for row_number, player in enumerate(design.sorted_players, start=1):
            players.append(
                {
                    "no": row_number,
                    "name": player.player_name,
                    "number": player.player_number,
                    "size": player.size,
                    "notes": player.notes,
                }
            )
        title = str(design.design_name or "").strip() or f"Desain {design_index}"
        groups.append(
            {
                "title": title,
                "item_label": design.primary_item_label,
                "players": players,
                "total": len(players),
            }
        )
    return groups


def customer_portal_player_rows(order):
    rows = []
    row_number = 1
    for design in sorted(order.designs, key=lambda item: (item.sort_order, item.id)):
        for player in design.sorted_players:
            rows.append(
                {
                    "no": row_number,
                    "name": player.player_name,
                    "number": player.player_number,
                    "size": player.size,
                    "notes": player.notes,
                }
            )
            row_number += 1
    return rows


def customer_portal_size_recap(order):
    grouped = {"Kids": {}, "Women": {}, "Reguler": {}}
    first_index = 0
    for design in sorted(order.designs, key=lambda item: (item.sort_order, item.id)):
        recap = design.size_recap
        for group_name in ("Kids", "Women", "Reguler"):
            for row in recap["groups"].get(group_name, []):
                first_index += 1
                key = normalize_size_key(row["size"]) or str(row["size"]).casefold()
                target = grouped[group_name].setdefault(
                    key,
                    {"size": row["size"], "qty": 0, "_first_index": first_index},
                )
                target["qty"] += row["qty"]
    return {
        group_name: [{"size": row["size"], "qty": row["qty"]} for row in sort_size_rows(rows.values())]
        for group_name, rows in grouped.items()
        if rows
    }


def customer_portal_long_sleeve_recap(order):
    rows_by_size = {}
    first_index = 0
    for design in sorted(order.designs, key=lambda item: (item.sort_order, item.id)):
        for row in design.long_sleeve_recap:
            first_index += 1
            base_size = long_sleeve_size_label(row["size"]) or str(row["size"]).strip()
            sleeve_type = long_sleeve_type_label(row["size"])
            key = (normalize_size_key(base_size) or base_size.casefold(), sleeve_type)
            target = rows_by_size.setdefault(
                key,
                {
                    "size": row["size"],
                    "base_size": base_size,
                    "sleeve_type": sleeve_type,
                    "qty": 0,
                    "_first_index": first_index,
                },
            )
            target["qty"] += row["qty"]
    return [{"size": row["size"], "qty": row["qty"]} for row in sort_long_sleeve_rows(rows_by_size.values())]


def _send_production_photo_file(photo, as_attachment):
    stored_path = str(photo.file_path or "")
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    if stored_path.startswith("uploads/"):
        relative_upload_path = stored_path.removeprefix("uploads/")
        file_path = upload_root.parent / stored_path if upload_root.name == "uploads" else upload_root / relative_upload_path
        allowed_root = upload_root
    else:
        file_path = Path(current_app.static_folder) / stored_path
        allowed_root = Path(current_app.static_folder).resolve()
    try:
        file_path.resolve().relative_to(allowed_root)
    except ValueError:
        abort(404)
    if not file_path.exists():
        abort(404)
    download_name = photo.original_filename or file_path.name
    return send_file(file_path, as_attachment=as_attachment, download_name=download_name)


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    register_filters(app)
    app.jinja_env.globals["active_class"] = active_class
    app.jinja_env.globals["has_permission"] = has_permission
    app.jinja_env.globals["display_nota_number"] = display_nota_number

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(sales_orders_bp)
    app.register_blueprint(sales_orders_approval_bp)
    app.register_blueprint(production_bp)
    app.register_blueprint(handover_bp)
    app.register_blueprint(master_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(nota_bp)
    app.register_blueprint(crm_bp)
    app.register_blueprint(tracking_bp)

    @app.before_request
    def keep_staff_session_persistent():
        if current_user.is_authenticated:
            session.permanent = True

    @app.route("/")
    def root():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.index") if current_user.is_admin else url_for("sales_orders.index"))
        return redirect(url_for("auth.login"))

    @app.route("/login", methods=["GET", "POST"])
    def login_alias():
        return login()

    @app.route("/track/<access_code>")
    def tracking_short_alias(access_code):
        return redirect(url_for("tracking.detail", access_code=access_code))

    @app.route("/track/<access_code>/approve", methods=["POST"])
    def tracking_approve_short_alias(access_code):
        return approve_customer(access_code)

    @app.route("/t/<tracking_code>")
    def public_tracking_detail(tracking_code):
        return _render_tracking_detail(get_sales_order_by_tracking_code(tracking_code))

    @app.route("/t/<tracking_code>/approve", methods=["POST"])
    def public_tracking_approve(tracking_code):
        order = get_sales_order_by_tracking_code(tracking_code)
        approve_customer_order(order)
        return redirect(url_for("public_tracking_detail", tracking_code=order.tracking_code))

    @app.route("/t/<tracking_code>/production-photos/<int:photo_id>")
    def public_tracking_production_photo(tracking_code, photo_id):
        order = get_sales_order_by_tracking_code(tracking_code)
        if not order or not customer_can_view_production_photos(order):
            abort(404)
        photo = get_photo_for_order(order, photo_id)
        return _send_production_photo_file(photo, as_attachment=False)

    @app.route("/t/<tracking_code>/production-photos/<int:photo_id>/download")
    def public_tracking_production_photo_download(tracking_code, photo_id):
        order = get_sales_order_by_tracking_code(tracking_code)
        if not order or not customer_can_view_production_photos(order):
            abort(404)
        photo = get_photo_for_order(order, photo_id)
        return _send_production_photo_file(photo, as_attachment=True)

    @app.route("/t/<tracking_code>/surat-order.pdf")
    def public_tracking_sales_order_download(tracking_code):
        return _sales_order_download_for_order(get_sales_order_by_tracking_code(tracking_code))

    @app.route("/t/<tracking_code>/nota.pdf")
    def public_tracking_nota_download(tracking_code):
        return _nota_download_for_order(get_sales_order_by_tracking_code(tracking_code))

    @app.route("/customer/access", methods=["GET", "POST"])
    def customer_access_alias():
        if request.method == "POST":
            access_record = find_by_access_code(request.form.get("access_code", "").strip())
            if access_record:
                return redirect(url_for("tracking.detail", access_code=access_record.access_code))
            flash("Kode akses tidak ditemukan.", "danger")
        return render_template("so/customer_access.html")

    @app.route("/so/")
    @permission_required("sales_order.view")
    def sales_order_alias():
        return redirect(url_for("sales_orders.index", **request.args))

    @app.route("/master-data")
    @permission_required("master.view")
    def master_data_alias():
        return redirect(url_for("master.index"))

    @app.route("/laporan")
    @permission_required("reports.view")
    def laporan_alias():
        return redirect(url_for("reports.index", **request.args))

    @app.route("/laporan/pdf")
    @permission_required("reports.view")
    def laporan_pdf_alias():
        return redirect(url_for("reports.pdf", **request.args))

    @app.route("/setting")
    @permission_required("settings.view")
    def setting_alias():
        return redirect(url_for("settings.index"))

    @app.route("/dev/seed-production-sample")
    def dev_seed_production_sample():
        return seed_production_sample_data()

    with app.app_context():
        ensure_upload_folders()
        db.create_all()
        ensure_database_schema_migrations()
        ensure_tracking_codes()
        seed_initial_data()
        seed_default_whatsapp_templates()
        backfill_crm_data()
        db.session.commit()

    return app


def ensure_database_schema_migrations():
    ensure_v04_schema()
    ensure_v05_schema()
    ensure_v06_schema()
    ensure_v07_schema()
    ensure_v08_crm_schema()
    ensure_v08_tracking_schema()
    ensure_design_material_schema()
    ensure_qc_schema()
    ensure_handover_schema()


def seed_initial_data():
    v06_marker = Setting.query.filter_by(key="erp_v06_default_users_seeded").first()
    default_users = [
        ("Administrator", "admin", "admin", "admin"),
        ("Desain", "desain", "desain", "desain"),
        ("Produksi", "produksi", "produksi", "produksi"),
    ]
    for name, username, password, role in default_users:
        user = User.query.filter_by(username=username).first()
        created = False
        if not user:
            user = User(name=name, username=username, role=role)
            db.session.add(user)
            created = True
        user.name = user.name or name
        user.role = role
        user.is_active = True
        if created or not v06_marker:
            user.set_password(password)

    if not v06_marker:
        db.session.add(Setting(key="erp_v06_default_users_seeded", value="1"))

    if Brand.query.first() is None:
        db.session.add(Brand(code="EVPRO", name="Evpro", color="#c5162e", point_per_size=1))
        db.session.add(Brand(code="RDR", name="RDR Apparel", color="#c5162e", point_per_size=1))
        db.session.add(Brand(code="FF", name="FF Apparel", color="#20242a", point_per_size=1))

    _seed_master_items()
    _seed_master(MasterMaterial, ["Milano", "Dryfit"])
    _seed_master(MasterPattern, ["Reguler", "Raglan"])
    _seed_master(MasterInstruction, ["Default"])
    seed_default_nota_products()
    db.session.commit()


def ensure_v04_schema():
    inspector = inspect(db.engine)
    if "notas" not in inspector.get_table_names():
        return

    nota_columns = {column["name"] for column in inspector.get_columns("notas")}
    if "so_id" not in nota_columns:
        db.session.execute(text("ALTER TABLE notas ADD COLUMN so_id INTEGER"))
        db.session.commit()

    indexes = inspector.get_indexes("notas")
    has_unique_so_index = any(index.get("unique") and index.get("column_names") == ["so_id"] for index in indexes)
    index_names = {index["name"] for index in indexes}
    if not has_unique_so_index and "ix_notas_so_id_unique" not in index_names:
        dialect_name = db.engine.dialect.name
        if dialect_name == "sqlite":
            db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_notas_so_id_unique ON notas (so_id) WHERE so_id IS NOT NULL"))
        else:
            db.session.execute(text("CREATE UNIQUE INDEX ix_notas_so_id_unique ON notas (so_id)"))
        db.session.commit()


def ensure_v05_schema():
    inspector = inspect(db.engine)
    if "sales_orders" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("sales_orders")}
    schema_changes = {
        "production_vendor": "ALTER TABLE sales_orders ADD COLUMN production_vendor VARCHAR(80)",
        "production_vendor_deadline": "ALTER TABLE sales_orders ADD COLUMN production_vendor_deadline DATE",
        "production_assigned_at": "ALTER TABLE sales_orders ADD COLUMN production_assigned_at DATETIME",
        "warehouse_received_at": "ALTER TABLE sales_orders ADD COLUMN warehouse_received_at DATETIME",
        "setting_by_name": "ALTER TABLE sales_orders ADD COLUMN setting_by_name VARCHAR(120)",
    }
    for column_name, statement in schema_changes.items():
        if column_name not in columns:
            db.session.execute(text(statement))
    db.session.commit()

    refreshed_columns = {column["name"] for column in inspect(db.engine).get_columns("sales_orders")}
    if "tanggal_finish_produksi" in refreshed_columns:
        db.session.execute(
            text(
                """
                UPDATE sales_orders
                SET tanggal_finish_produksi = COALESCE(production_status_updated_at, updated_at, created_at)
                WHERE production_status IN ('Finish', 'Selesai')
                  AND tanggal_finish_produksi IS NULL
                """
            )
        )
        db.session.commit()


def ensure_v06_schema():
    inspector = inspect(db.engine)
    if "users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "role" not in columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(30) NOT NULL DEFAULT 'admin'"))
        if "is_active" not in columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
        db.session.commit()


def ensure_v07_schema():
    inspector = inspect(db.engine)
    if "sales_order_production_photos" in inspector.get_table_names():
        return
    db.session.execute(
        text(
            """
            CREATE TABLE sales_order_production_photos (
                id INTEGER NOT NULL PRIMARY KEY,
                sales_order_id INTEGER NOT NULL,
                file_path VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255),
                sort_order INTEGER NOT NULL DEFAULT 0,
                uploaded_by_id INTEGER,
                created_at DATETIME NOT NULL,
                FOREIGN KEY(sales_order_id) REFERENCES sales_orders (id),
                FOREIGN KEY(uploaded_by_id) REFERENCES users (id)
            )
            """
        )
    )
    db.session.execute(text("CREATE INDEX ix_sales_order_production_photos_sales_order_id ON sales_order_production_photos (sales_order_id)"))
    db.session.commit()


def ensure_v08_tracking_schema():
    if not _table_exists("sales_orders"):
        return
    _add_column_if_missing("sales_orders", "tracking_code", "VARCHAR(20)")


def ensure_v09_tracking_schema():
    ensure_v08_tracking_schema()


def ensure_design_material_schema():
    if not _table_exists("sales_order_designs"):
        return
    _add_column_if_missing("sales_order_designs", "top_material", "VARCHAR(120)")
    _add_column_if_missing("sales_order_designs", "bottom_material", "VARCHAR(120)")


def ensure_tracking_codes():
    if not _table_exists("sales_orders") or "tracking_code" not in _table_columns("sales_orders"):
        return
    for order in SalesOrder.query.filter((SalesOrder.tracking_code.is_(None)) | (SalesOrder.tracking_code == "")).all():
        order.tracking_code = generate_tracking_code()
    db.session.commit()
    _create_index_if_missing("ix_sales_orders_tracking_code", "sales_orders", "tracking_code", unique=True)


def ensure_qc_schema():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    if "sales_orders" in tables:
        columns = {column["name"] for column in inspector.get_columns("sales_orders")}
        if "shortage_note" not in columns:
            db.session.execute(text("ALTER TABLE sales_orders ADD COLUMN shortage_note TEXT"))
            db.session.commit()
        if "qc_note" not in columns:
            db.session.execute(text("ALTER TABLE sales_orders ADD COLUMN qc_note TEXT"))
            db.session.commit()

    if "qc_checklists" not in tables:
        db.session.execute(
            text(
                """
                CREATE TABLE qc_checklists (
                    id INTEGER NOT NULL PRIMARY KEY,
                    sales_order_id INTEGER NOT NULL,
                    sales_order_player_id INTEGER NOT NULL,
                    qc_jersey BOOLEAN NOT NULL DEFAULT 0,
                    cek_jersey BOOLEAN NOT NULL DEFAULT 0,
                    qc_celana BOOLEAN NOT NULL DEFAULT 0,
                    cek_celana BOOLEAN NOT NULL DEFAULT 0,
                    qc_data TEXT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    FOREIGN KEY(sales_order_id) REFERENCES sales_orders (id),
                    FOREIGN KEY(sales_order_player_id) REFERENCES sales_order_players (id),
                    UNIQUE (sales_order_player_id)
                )
                """
            )
        )
        db.session.execute(text("CREATE INDEX ix_qc_checklists_sales_order_id ON qc_checklists (sales_order_id)"))
        db.session.execute(text("CREATE INDEX ix_qc_checklists_sales_order_player_id ON qc_checklists (sales_order_player_id)"))
        db.session.commit()
    else:
        qc_columns = {column["name"] for column in inspector.get_columns("qc_checklists")}
        if "qc_data" not in qc_columns:
            db.session.execute(text("ALTER TABLE qc_checklists ADD COLUMN qc_data TEXT"))
            db.session.commit()

    if "master_items" in tables:
        item_columns = {column["name"] for column in inspector.get_columns("master_items")}
        item_changes = {
            "perlu_upload_gambar": "ALTER TABLE master_items ADD COLUMN perlu_upload_gambar BOOLEAN NOT NULL DEFAULT 1",
            "perlu_qc": "ALTER TABLE master_items ADD COLUMN perlu_qc BOOLEAN NOT NULL DEFAULT 1",
        }
        for column_name, statement in item_changes.items():
            if column_name not in item_columns:
                db.session.execute(text(statement))
        db.session.commit()


def ensure_handover_schema():
    inspector = inspect(db.engine)
    if "sales_orders" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("sales_orders")}
    schema_changes = {
        "tanggal_finish_produksi": "ALTER TABLE sales_orders ADD COLUMN tanggal_finish_produksi DATETIME",
        "tanggal_pengambilan": "ALTER TABLE sales_orders ADD COLUMN tanggal_pengambilan DATE",
        "diambil_oleh": "ALTER TABLE sales_orders ADD COLUMN diambil_oleh VARCHAR(150)",
        "catatan_pengambilan": "ALTER TABLE sales_orders ADD COLUMN catatan_pengambilan TEXT",
        "serah_terima_admin_id": "ALTER TABLE sales_orders ADD COLUMN serah_terima_admin_id INTEGER",
    }
    for column_name, statement in schema_changes.items():
        if column_name not in columns:
            db.session.execute(text(statement))
    db.session.commit()


def _quote_identifier(identifier):
    return '"' + str(identifier).replace('"', '""') + '"'


def _table_exists(table_name):
    result = db.session.execute(
        text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :table_name"),
        {"table_name": table_name},
    ).first()
    return bool(result)


def _table_columns(table_name):
    if not _table_exists(table_name):
        return set()
    quoted_table = _quote_identifier(table_name)
    rows = db.session.execute(text(f"PRAGMA table_info({quoted_table})")).mappings().all()
    return {row["name"] for row in rows}


def _add_column_if_missing(table_name, column_name, column_definition):
    if not _table_exists(table_name):
        return
    if column_name in _table_columns(table_name):
        return
    db.session.execute(
        text(
            f"ALTER TABLE {_quote_identifier(table_name)} "
            f"ADD COLUMN {_quote_identifier(column_name)} {column_definition}"
        )
    )
    db.session.commit()


def _create_index_if_missing(index_name, table_name, columns, unique=False):
    if not _table_exists(table_name):
        return
    column_list = columns if isinstance(columns, (list, tuple)) else [columns]
    existing = db.session.execute(
        text("SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = :index_name"),
        {"index_name": index_name},
    ).first()
    if existing:
        return
    unique_sql = "UNIQUE " if unique else ""
    quoted_columns = ", ".join(_quote_identifier(column) for column in column_list)
    db.session.execute(
        text(
            f"CREATE {unique_sql}INDEX {_quote_identifier(index_name)} "
            f"ON {_quote_identifier(table_name)} ({quoted_columns})"
        )
    )
    db.session.commit()


def ensure_v08_crm_schema():
    if not _table_exists("customers"):
        db.session.execute(
            text(
                """
                CREATE TABLE customers (
                    id INTEGER NOT NULL PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    whatsapp VARCHAR(50),
                    address TEXT,
                    source VARCHAR(50) NOT NULL DEFAULT 'Ahmad',
                    source_name VARCHAR(150),
                    first_order_date DATE,
                    total_sales_orders INTEGER NOT NULL DEFAULT 0,
                    total_notas INTEGER NOT NULL DEFAULT 0,
                    status VARCHAR(30) NOT NULL DEFAULT 'Baru',
                    character_notes TEXT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )
        db.session.execute(text("CREATE INDEX ix_customers_name ON customers (name)"))
        db.session.execute(text("CREATE INDEX ix_customers_whatsapp ON customers (whatsapp)"))
        db.session.execute(text("CREATE INDEX ix_customers_source ON customers (source)"))
        db.session.execute(text("CREATE INDEX ix_customers_status ON customers (status)"))
        db.session.execute(text("CREATE INDEX ix_customers_first_order_date ON customers (first_order_date)"))
        db.session.commit()
    else:
        _add_column_if_missing("customers", "name", "VARCHAR(150)")
        _add_column_if_missing("customers", "whatsapp", "VARCHAR(50)")
        _add_column_if_missing("customers", "address", "TEXT")
        _add_column_if_missing("customers", "source", "VARCHAR(50) NOT NULL DEFAULT 'Ahmad'")
        _add_column_if_missing("customers", "source_name", "VARCHAR(150)")
        _add_column_if_missing("customers", "first_order_date", "DATE")
        _add_column_if_missing("customers", "total_sales_orders", "INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing("customers", "total_notas", "INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing("customers", "status", "VARCHAR(30) NOT NULL DEFAULT 'Baru'")
        _add_column_if_missing("customers", "character_notes", "TEXT")
        _add_column_if_missing("customers", "created_at", "DATETIME")
        _add_column_if_missing("customers", "updated_at", "DATETIME")
    _create_index_if_missing("ix_customers_name", "customers", "name")
    _create_index_if_missing("ix_customers_whatsapp", "customers", "whatsapp")
    _create_index_if_missing("ix_customers_source", "customers", "source")
    _create_index_if_missing("ix_customers_status", "customers", "status")
    _create_index_if_missing("ix_customers_first_order_date", "customers", "first_order_date")

    if not _table_exists("leads"):
        db.session.execute(
            text(
                """
                CREATE TABLE leads (
                    id INTEGER NOT NULL PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    whatsapp VARCHAR(50),
                    source VARCHAR(50) NOT NULL DEFAULT 'WhatsApp',
                    source_detail VARCHAR(150),
                    need_type VARCHAR(150),
                    estimated_qty INTEGER,
                    notes TEXT,
                    status VARCHAR(50) NOT NULL DEFAULT 'Baru masuk',
                    next_follow_up_date DATE,
                    assigned_to INTEGER,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    converted_customer_id INTEGER,
                    converted_so_id INTEGER,
                    FOREIGN KEY(assigned_to) REFERENCES users (id),
                    FOREIGN KEY(converted_customer_id) REFERENCES customers (id),
                    FOREIGN KEY(converted_so_id) REFERENCES sales_orders (id)
                )
                """
            )
        )
        db.session.commit()
    else:
        _add_column_if_missing("leads", "name", "VARCHAR(150)")
        _add_column_if_missing("leads", "whatsapp", "VARCHAR(50)")
        _add_column_if_missing("leads", "source", "VARCHAR(50) NOT NULL DEFAULT 'WhatsApp'")
        _add_column_if_missing("leads", "source_detail", "VARCHAR(150)")
        _add_column_if_missing("leads", "need_type", "VARCHAR(150)")
        _add_column_if_missing("leads", "estimated_qty", "INTEGER")
        _add_column_if_missing("leads", "notes", "TEXT")
        _add_column_if_missing("leads", "status", "VARCHAR(50) NOT NULL DEFAULT 'Baru masuk'")
        _add_column_if_missing("leads", "next_follow_up_date", "DATE")
        _add_column_if_missing("leads", "assigned_to", "INTEGER")
        _add_column_if_missing("leads", "created_at", "DATETIME")
        _add_column_if_missing("leads", "updated_at", "DATETIME")
        _add_column_if_missing("leads", "converted_customer_id", "INTEGER")
        _add_column_if_missing("leads", "converted_so_id", "INTEGER")
    _create_index_if_missing("ix_leads_name", "leads", "name")
    _create_index_if_missing("ix_leads_whatsapp", "leads", "whatsapp")
    _create_index_if_missing("ix_leads_source", "leads", "source")
    _create_index_if_missing("ix_leads_status", "leads", "status")
    _create_index_if_missing("ix_leads_next_follow_up_date", "leads", "next_follow_up_date")
    _create_index_if_missing("ix_leads_assigned_to", "leads", "assigned_to")
    _create_index_if_missing("ix_leads_converted_customer_id", "leads", "converted_customer_id")
    _create_index_if_missing("ix_leads_converted_so_id", "leads", "converted_so_id")

    if not _table_exists("follow_ups"):
        db.session.execute(
            text(
                """
                CREATE TABLE follow_ups (
                    id INTEGER NOT NULL PRIMARY KEY,
                    follow_up_type VARCHAR(20) NOT NULL DEFAULT 'Customer',
                    lead_id INTEGER,
                    customer_id INTEGER,
                    follow_up_date DATE NOT NULL,
                    admin_id INTEGER,
                    admin_name VARCHAR(120),
                    content TEXT NOT NULL,
                    customer_response TEXT,
                    status VARCHAR(50) NOT NULL DEFAULT 'Belum dihubungi',
                    next_follow_up_date DATE,
                    notes TEXT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    FOREIGN KEY(lead_id) REFERENCES leads (id),
                    FOREIGN KEY(customer_id) REFERENCES customers (id),
                    FOREIGN KEY(admin_id) REFERENCES users (id)
                )
                """
            )
        )
        db.session.commit()
    else:
        _add_column_if_missing("follow_ups", "follow_up_type", "VARCHAR(20) NOT NULL DEFAULT 'Customer'")
        _add_column_if_missing("follow_ups", "lead_id", "INTEGER")
        _add_column_if_missing("follow_ups", "customer_id", "INTEGER")
        _add_column_if_missing("follow_ups", "follow_up_date", "DATE")
        _add_column_if_missing("follow_ups", "admin_id", "INTEGER")
        _add_column_if_missing("follow_ups", "admin_name", "VARCHAR(120)")
        _add_column_if_missing("follow_ups", "content", "TEXT")
        _add_column_if_missing("follow_ups", "customer_response", "TEXT")
        _add_column_if_missing("follow_ups", "status", "VARCHAR(50) NOT NULL DEFAULT 'Belum dihubungi'")
        _add_column_if_missing("follow_ups", "next_follow_up_date", "DATE")
        _add_column_if_missing("follow_ups", "notes", "TEXT")
        _add_column_if_missing("follow_ups", "created_at", "DATETIME")
        _add_column_if_missing("follow_ups", "updated_at", "DATETIME")
        db.session.execute(text("UPDATE follow_ups SET follow_up_type = 'Customer' WHERE follow_up_type IS NULL OR follow_up_type = ''"))
        db.session.commit()
        _ensure_follow_ups_customer_nullable()
    _create_index_if_missing("ix_follow_ups_customer_id", "follow_ups", "customer_id")
    _create_index_if_missing("ix_follow_ups_lead_id", "follow_ups", "lead_id")
    _create_index_if_missing("ix_follow_ups_follow_up_type", "follow_ups", "follow_up_type")
    _create_index_if_missing("ix_follow_ups_admin_id", "follow_ups", "admin_id")
    _create_index_if_missing("ix_follow_ups_follow_up_date", "follow_ups", "follow_up_date")
    _create_index_if_missing("ix_follow_ups_next_follow_up_date", "follow_ups", "next_follow_up_date")
    _create_index_if_missing("ix_follow_ups_status", "follow_ups", "status")

    if not _table_exists("whatsapp_templates"):
        db.session.execute(
            text(
                """
                CREATE TABLE whatsapp_templates (
                    id INTEGER NOT NULL PRIMARY KEY,
                    key VARCHAR(80) NOT NULL UNIQUE,
                    name VARCHAR(150) NOT NULL,
                    category VARCHAR(80) NOT NULL,
                    content TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 1,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    is_deleted BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )
        db.session.execute(text("CREATE INDEX ix_whatsapp_templates_key ON whatsapp_templates (key)"))
        db.session.execute(text("CREATE INDEX ix_whatsapp_templates_category ON whatsapp_templates (category)"))
        db.session.execute(text("CREATE INDEX ix_whatsapp_templates_sort_order ON whatsapp_templates (sort_order)"))
        db.session.execute(text("CREATE INDEX ix_whatsapp_templates_is_active ON whatsapp_templates (is_active)"))
        db.session.execute(text("CREATE INDEX ix_whatsapp_templates_is_deleted ON whatsapp_templates (is_deleted)"))
        db.session.commit()
    else:
        _add_column_if_missing("whatsapp_templates", "key", "VARCHAR(80)")
        _add_column_if_missing("whatsapp_templates", "name", "VARCHAR(150)")
        _add_column_if_missing("whatsapp_templates", "category", "VARCHAR(80)")
        _add_column_if_missing("whatsapp_templates", "content", "TEXT")
        _add_column_if_missing("whatsapp_templates", "sort_order", "INTEGER NOT NULL DEFAULT 1")
        _add_column_if_missing("whatsapp_templates", "is_active", "BOOLEAN NOT NULL DEFAULT 1")
        _add_column_if_missing("whatsapp_templates", "is_deleted", "BOOLEAN NOT NULL DEFAULT 0")
        _add_column_if_missing("whatsapp_templates", "created_at", "DATETIME")
        _add_column_if_missing("whatsapp_templates", "updated_at", "DATETIME")
        db.session.execute(text("UPDATE whatsapp_templates SET sort_order = id WHERE sort_order IS NULL OR sort_order = 0"))
        db.session.execute(text("UPDATE whatsapp_templates SET is_deleted = 0 WHERE is_deleted IS NULL"))
        sort_stats = db.session.execute(
            text("SELECT COUNT(*) AS total, COUNT(DISTINCT sort_order) AS distinct_total FROM whatsapp_templates WHERE is_deleted = 0")
        ).mappings().first()
        if sort_stats and sort_stats["total"] > 1 and sort_stats["distinct_total"] <= 1:
            db.session.execute(text("UPDATE whatsapp_templates SET sort_order = id WHERE is_deleted = 0"))
        db.session.commit()
    _create_index_if_missing("ix_whatsapp_templates_key", "whatsapp_templates", "key")
    _create_index_if_missing("ix_whatsapp_templates_category", "whatsapp_templates", "category")
    _create_index_if_missing("ix_whatsapp_templates_sort_order", "whatsapp_templates", "sort_order")
    _create_index_if_missing("ix_whatsapp_templates_is_active", "whatsapp_templates", "is_active")
    _create_index_if_missing("ix_whatsapp_templates_is_deleted", "whatsapp_templates", "is_deleted")

    if _table_exists("sales_orders"):
        _add_column_if_missing("sales_orders", "crm_customer_id", "INTEGER")
        _create_index_if_missing("ix_sales_orders_crm_customer_id", "sales_orders", "crm_customer_id")

    if _table_exists("notas"):
        _add_column_if_missing("notas", "crm_customer_id", "INTEGER")
        _create_index_if_missing("ix_notas_crm_customer_id", "notas", "crm_customer_id")

    db.session.commit()


def _ensure_follow_ups_customer_nullable():
    inspector = inspect(db.engine)
    if db.engine.dialect.name != "sqlite" or "follow_ups" not in inspector.get_table_names():
        return
    columns = inspector.get_columns("follow_ups")
    customer_column = next((column for column in columns if column["name"] == "customer_id"), None)
    if not customer_column or customer_column.get("nullable", True):
        return
    db.session.execute(text("ALTER TABLE follow_ups RENAME TO follow_ups_old"))
    db.session.execute(
        text(
            """
            CREATE TABLE follow_ups (
                id INTEGER NOT NULL PRIMARY KEY,
                follow_up_type VARCHAR(20) NOT NULL DEFAULT 'Customer',
                lead_id INTEGER,
                customer_id INTEGER,
                follow_up_date DATE NOT NULL,
                admin_id INTEGER,
                admin_name VARCHAR(120),
                content TEXT NOT NULL,
                customer_response TEXT,
                status VARCHAR(50) NOT NULL DEFAULT 'Belum dihubungi',
                next_follow_up_date DATE,
                notes TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY(lead_id) REFERENCES leads (id),
                FOREIGN KEY(customer_id) REFERENCES customers (id),
                FOREIGN KEY(admin_id) REFERENCES users (id)
            )
            """
        )
    )
    db.session.execute(
        text(
            """
            INSERT INTO follow_ups (
                id, follow_up_type, lead_id, customer_id, follow_up_date, admin_id, admin_name,
                content, customer_response, status, next_follow_up_date, notes, created_at, updated_at
            )
            SELECT
                id,
                COALESCE(NULLIF(follow_up_type, ''), 'Customer'),
                lead_id,
                customer_id,
                follow_up_date,
                admin_id,
                admin_name,
                content,
                customer_response,
                status,
                next_follow_up_date,
                notes,
                created_at,
                updated_at
            FROM follow_ups_old
            """
        )
    )
    db.session.execute(text("DROP TABLE follow_ups_old"))
    db.session.execute(text("CREATE INDEX ix_follow_ups_customer_id ON follow_ups (customer_id)"))
    db.session.execute(text("CREATE INDEX ix_follow_ups_lead_id ON follow_ups (lead_id)"))
    db.session.execute(text("CREATE INDEX ix_follow_ups_follow_up_type ON follow_ups (follow_up_type)"))
    db.session.execute(text("CREATE INDEX ix_follow_ups_admin_id ON follow_ups (admin_id)"))
    db.session.execute(text("CREATE INDEX ix_follow_ups_follow_up_date ON follow_ups (follow_up_date)"))
    db.session.execute(text("CREATE INDEX ix_follow_ups_next_follow_up_date ON follow_ups (next_follow_up_date)"))
    db.session.execute(text("CREATE INDEX ix_follow_ups_status ON follow_ups (status)"))
    db.session.commit()


def backfill_crm_data():
    from models import Nota, SalesOrder

    marker = Setting.query.filter_by(key="erp_v08_crm_backfilled").first()
    if marker:
        return
    for order in SalesOrder.query.filter_by(is_deleted=False).order_by(SalesOrder.created_at.asc()).all():
        sync_sales_order_customer(order)
    for nota in Nota.query.order_by(Nota.order_date.asc(), Nota.id.asc()).all():
        sync_nota_customer(nota)
    refresh_all_customer_stats()
    db.session.add(Setting(key="erp_v08_crm_backfilled", value="1"))
    db.session.commit()


def _seed_master_items():
    defaults = ["Jersey", "Celana", "Jersey + Celana", "Jaket", "Training"]
    existing = {row.name for row in MasterItem.query.all()}
    next_order = (db.session.query(db.func.max(MasterItem.sort_order)).scalar() or 0) + 1
    for name in defaults:
        if name not in existing:
            db.session.add(
                MasterItem(
                    name=name,
                    status="active",
                    sort_order=next_order,
                    perlu_upload_gambar=True,
                    perlu_qc=True,
                )
            )
            next_order += 1


def _seed_master(model, names):
    if model.query.first() is not None:
        return
    existing = {row.name for row in model.query.all()}
    for index, name in enumerate(names, start=1):
        if name not in existing:
            db.session.add(model(name=name, status="active", sort_order=index))


app = create_app()


if __name__ == "__main__":
    app.run(
        host=Config.APP_HOST,
        port=Config.APP_PORT,
        debug=True,
    )
