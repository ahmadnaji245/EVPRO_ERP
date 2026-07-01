#!/usr/bin/env python3
import argparse
import shutil
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT.parent / "ERP_SO"
DEFAULT_SOURCE_DB = SOURCE_ROOT / "instance" / "erp_so.db"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app  # noqa: E402
from database.db import db  # noqa: E402
from models import Brand, MasterInstruction, MasterItem, MasterMaterial, MasterPattern, Nota, SalesOrder, User  # noqa: E402
from sqlalchemy import text  # noqa: E402


MASTER_TABLES = {
    "items": ("master_items", MasterItem),
    "materials": ("master_materials", MasterMaterial),
    "patterns": ("master_patterns", MasterPattern),
    "instructions": ("master_instructions", MasterInstruction),
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Import master data Sales Order dari ERP_SO ke EVPRO ERP.")
    parser.add_argument(
        "--source-db",
        default=str(DEFAULT_SOURCE_DB),
        help="Path database SQLite ERP_SO. Default: ../ERP_SO/instance/erp_so.db",
    )
    return parser.parse_args()


def _connect(source_db):
    source_path = Path(source_db).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Database ERP_SO tidak ditemukan: {source_path}")
    connection = sqlite3.connect(source_path)
    connection.row_factory = sqlite3.Row
    return source_path, connection


def _rows(connection, table, columns="*"):
    return [dict(row) for row in connection.execute(f"SELECT {columns} FROM {table} ORDER BY id").fetchall()]


def _normalize_code(value):
    return "".join(char for char in str(value or "").strip().upper() if char.isalnum())


def _normalize_name(value):
    return " ".join(str(value or "").strip().casefold().split())


def _has_transaction_for_brand(brand):
    so_count = SalesOrder.query.filter_by(brand_id=brand.id).count()
    nota_count = Nota.query.filter_by(brand_id=brand.id).count()
    return so_count + nota_count > 0


def _copy_logo(logo_path):
    logo_path = str(logo_path or "").strip()
    if not logo_path:
        return None

    source_file = SOURCE_ROOT / "static" / logo_path
    if not source_file.exists():
        return None

    target_file = PROJECT_ROOT / "static" / logo_path
    target_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_file, target_file)
    return logo_path


def _find_brand(row):
    source_code = _normalize_code(row.get("code"))
    brand = Brand.query.filter(db.func.upper(Brand.code) == source_code).first()
    if brand:
        return brand

    source_name = _normalize_name(row.get("name"))
    same_name = Brand.query.filter(db.func.lower(Brand.name) == source_name).all()
    if len(same_name) == 1:
        return same_name[0]
    return None


def _upsert_brands(rows):
    stats = {"source": len(rows), "created": 0, "updated": 0, "deactivated": 0, "deleted": 0, "logo_copied": []}
    source_codes = {_normalize_code(row.get("code")) for row in rows}

    for row in rows:
        code = _normalize_code(row.get("code"))
        name = str(row.get("name") or "").strip()
        if not code or not name:
            continue

        brand = _find_brand(row)
        if not brand:
            brand = Brand(code=code)
            db.session.add(brand)
            stats["created"] += 1
        else:
            stats["updated"] += 1

        copied_logo_path = _copy_logo(row.get("logo_path"))
        if copied_logo_path:
            stats["logo_copied"].append(copied_logo_path)

        brand.code = code
        brand.name = name
        brand.logo_path = copied_logo_path or row.get("logo_path") or None
        brand.color = row.get("color") or "#c5162e"
        brand.point_per_size = float(row.get("point_per_size") or 1)
        brand.status = row.get("status") or "active"
        brand.notes = row.get("notes") if row.get("notes") not in ("", "None") else None

    db.session.flush()

    for brand in Brand.query.all():
        if _normalize_code(brand.code) in source_codes:
            continue
        if _has_transaction_for_brand(brand):
            if brand.status != "inactive":
                brand.status = "inactive"
                stats["deactivated"] += 1
            continue
        db.session.delete(brand)
        stats["deleted"] += 1

    return stats


def _find_master_row(model, name):
    return model.query.filter(db.func.lower(model.name) == _normalize_name(name)).first()


def _upsert_simple_master(rows, model):
    stats = {"source": len(rows), "created": 0, "updated": 0, "deleted": 0, "skipped": 0}
    source_names = {_normalize_name(row.get("name")) for row in rows if str(row.get("name") or "").strip()}

    for row in rows:
        name = str(row.get("name") or "").strip()
        if not name:
            stats["skipped"] += 1
            continue
        record = _find_master_row(model, name)
        if not record:
            record = model(name=name)
            db.session.add(record)
            stats["created"] += 1
        else:
            stats["updated"] += 1
        record.name = name
        record.status = row.get("status") or "active"
        record.sort_order = int(row.get("sort_order") or 0)

    for record in model.query.all():
        if _normalize_name(record.name) not in source_names:
            db.session.delete(record)
            stats["deleted"] += 1

    return stats


def _upsert_users(rows):
    stats = {
        "source": len(rows),
        "created": 0,
        "updated": 0,
        "deleted": 0,
        "deactivated": 0,
        "skipped": 0,
        "reset_required": [],
    }
    source_usernames = {str(row.get("username") or "").strip() for row in rows if str(row.get("username") or "").strip()}

    for row in rows:
        username = str(row.get("username") or "").strip()
        password_hash = str(row.get("password_hash") or "").strip()
        if not username or not password_hash:
            stats["skipped"] += 1
            if username:
                stats["reset_required"].append(username)
            continue

        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, password_hash=password_hash)
            db.session.add(user)
            stats["created"] += 1
        else:
            stats["updated"] += 1
        user.name = str(row.get("name") or username).strip()
        user.password_hash = password_hash
        user.role = row.get("role") or "admin"
        user.is_active = bool(row.get("is_active"))

    for user in User.query.all():
        if user.username in source_usernames:
            continue
        if _has_user_reference(user.id):
            if user.is_active:
                user.is_active = False
                stats["deactivated"] += 1
            continue
        db.session.delete(user)
        stats["deleted"] += 1

    return stats


def _has_user_reference(user_id):
    checks = [
        ("sales_orders", "created_by_id = :user_id"),
        ("revision_histories", "user_id = :user_id"),
        ("notas", "created_by_id = :user_id"),
        (
            "production_checklists",
            "setting_user_id = :user_id OR qc_user_id = :user_id OR finish_user_id = :user_id "
            "OR setting_done_by_user_id = :user_id OR qc_done_by_user_id = :user_id",
        ),
        ("production_size_checklists", "setting_user_id = :user_id"),
    ]
    for table, where_clause in checks:
        result = db.session.execute(
            text(f"SELECT COUNT(*) FROM {table} WHERE {where_clause}"),
            {"user_id": user_id},
        ).scalar()
        if result:
            return True
    return False


def import_master_data(source_db):
    source_path, connection = _connect(source_db)
    try:
        source_tables = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        stats = {
            "source_db": str(source_path),
            "tables": [],
            "brands": {},
            "masters": {},
            "users": {},
        }

        with app.app_context():
            if "brands" in source_tables:
                stats["tables"].append("brands")
                stats["brands"] = _upsert_brands(_rows(connection, "brands"))

            for key, (table, model) in MASTER_TABLES.items():
                if table not in source_tables:
                    continue
                stats["tables"].append(table)
                stats["masters"][key] = _upsert_simple_master(_rows(connection, table), model)

            if "users" in source_tables:
                stats["tables"].append("users")
                stats["users"] = _upsert_users(_rows(connection, "users"))

            db.session.commit()
            stats["final_counts"] = {
                "brands": Brand.query.count(),
                "items": MasterItem.query.count(),
                "materials": MasterMaterial.query.count(),
                "patterns": MasterPattern.query.count(),
                "instructions": MasterInstruction.query.count(),
                "users": User.query.count(),
            }
        return stats
    finally:
        connection.close()


def _print_stats(stats):
    print(f"Database ERP_SO: {stats['source_db']}")
    print(f"Tabel ditemukan: {', '.join(stats['tables'])}")
    brand_stats = stats.get("brands", {})
    print(f"Brand sumber: {brand_stats.get('source', 0)}")
    print(f"Brand dibuat: {brand_stats.get('created', 0)}")
    print(f"Brand diupdate: {brand_stats.get('updated', 0)}")
    print(f"Brand lama dinonaktifkan: {brand_stats.get('deactivated', 0)}")
    print(f"Brand lama dihapus: {brand_stats.get('deleted', 0)}")
    print(f"Logo disalin: {len(brand_stats.get('logo_copied', []))}")
    for logo_path in brand_stats.get("logo_copied", []):
        print(f"  - {logo_path}")

    labels = {
        "items": "Item",
        "materials": "Material",
        "patterns": "Pola",
        "instructions": "Instruksi",
    }
    for key, label in labels.items():
        master_stats = stats.get("masters", {}).get(key, {})
        print(f"{label} sumber: {master_stats.get('source', 0)}")
        print(f"{label} dibuat: {master_stats.get('created', 0)}")
        print(f"{label} diupdate: {master_stats.get('updated', 0)}")
        print(f"{label} dihapus: {master_stats.get('deleted', 0)}")

    user_stats = stats.get("users", {})
    print(f"User sumber: {user_stats.get('source', 0)}")
    print(f"User dibuat: {user_stats.get('created', 0)}")
    print(f"User diupdate: {user_stats.get('updated', 0)}")
    print(f"User lama dihapus: {user_stats.get('deleted', 0)}")
    print(f"User lama dinonaktifkan: {user_stats.get('deactivated', 0)}")
    print(f"User dilewati: {user_stats.get('skipped', 0)}")
    if user_stats.get("reset_required"):
        print("User perlu reset password: " + ", ".join(user_stats["reset_required"]))

    print("Jumlah akhir ERP:")
    for key, value in stats.get("final_counts", {}).items():
        print(f"  {key}: {value}")


def main():
    args = _parse_args()
    _print_stats(import_master_data(args.source_db))


if __name__ == "__main__":
    main()
