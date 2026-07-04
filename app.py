from pathlib import Path

from flask import Blueprint, Flask, abort, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from sqlalchemy import inspect, text

from config import Config
from database.db import db
from models import Brand, MasterInstruction, MasterItem, MasterMaterial, MasterPattern, User
from routes.handover_routes import handover_bp
from routes.nota_routes import nota_bp
from routes.so_shell_routes import master_bp, production_bp, reports_bp, settings_bp
from routes.so_routes import sales_orders_approval_bp, sales_orders_bp
from services.dashboard_service import dashboard_stats, monthly_point_chart, monthly_setting_point_progress
from services.nota_service import seed_default_nota_products
from services.production_service import seed_production_sample_data
from utils.formatters import register_filters
from utils.helpers import active_class, ensure_upload_folders
from utils.constants import user_is_admin


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
@login_required
def index():
    if not user_is_admin(current_user):
        abort(403)
    return render_template(
        "dashboard.html",
        stats=dashboard_stats(),
        monthly=monthly_point_chart(),
        setting_progress=monthly_setting_point_progress(),
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    from flask import flash, request

    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index") if current_user.is_admin else url_for("sales_orders.index"))

    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username", "").strip()).first()
        if user and user.is_active and user.check_password(request.form.get("password", "")):
            login_user(user)
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
    return redirect(url_for("sales_orders.index"))


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    register_filters(app)
    app.jinja_env.globals["active_class"] = active_class

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
    app.register_blueprint(tracking_bp)

    @app.route("/")
    def root():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login"))

    @app.route("/login", methods=["GET", "POST"])
    def login_alias():
        return login()

    @app.route("/so/")
    @login_required
    def sales_order_alias():
        return redirect(url_for("sales_orders.index", **request.args))

    @app.route("/master-data")
    @login_required
    def master_data_alias():
        if not user_is_admin(current_user):
            abort(403)
        return redirect(url_for("master.index"))

    @app.route("/laporan")
    @login_required
    def laporan_alias():
        if not user_is_admin(current_user):
            abort(403)
        return redirect(url_for("reports.index", **request.args))

    @app.route("/laporan/pdf")
    @login_required
    def laporan_pdf_alias():
        if not user_is_admin(current_user):
            abort(403)
        return redirect(url_for("reports.pdf", **request.args))

    @app.route("/setting")
    @login_required
    def setting_alias():
        if not user_is_admin(current_user):
            abort(403)
        return redirect(url_for("settings.index"))

    @app.route("/dev/seed-production-sample")
    def dev_seed_production_sample():
        return seed_production_sample_data()

    with app.app_context():
        ensure_upload_folders()
        db.create_all()
        ensure_v04_schema()
        ensure_v05_schema()
        ensure_qc_schema()
        ensure_handover_schema()
        seed_initial_data()

    return app


def seed_initial_data():
    has_users = User.query.first() is not None
    if not has_users and not User.query.filter_by(username="admin").first():
        admin = User(name="Administrator", username="admin", role="admin")
        admin.set_password("admin")
        db.session.add(admin)

    if not has_users and not User.query.filter_by(username="produksi").first():
        produksi = User(name="Produksi", username="produksi", role="produksi")
        produksi.set_password("produksi")
        db.session.add(produksi)

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
