#!/usr/bin/env python3
import argparse
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DB = PROJECT_ROOT.parent / "Nota" / "database" / "nota.sqlite3"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app  # noqa: E402
from database.db import db  # noqa: E402
from models.nota import NotaProduct  # noqa: E402
from services.nota_service import get_product_by_code  # noqa: E402


def _parse_args():
    parser = argparse.ArgumentParser(description="Import produk Nota legacy ke EVPRO ERP.")
    parser.add_argument(
        "--source-db",
        default=str(DEFAULT_SOURCE_DB),
        help="Path database SQLite Nota lama. Default: ../Nota/database/nota.sqlite3",
    )
    return parser.parse_args()


def _read_legacy_products(source_db):
    source_path = Path(source_db).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Database lama tidak ditemukan: {source_path}")

    with sqlite3.connect(source_path) as connection:
        connection.row_factory = sqlite3.Row
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(products)").fetchall()
        }
        required_columns = {"code", "description", "price"}
        missing_columns = sorted(required_columns - columns)
        if missing_columns:
            raise RuntimeError(f"Kolom products tidak lengkap: {', '.join(missing_columns)}")

        return [
            dict(row)
            for row in connection.execute(
                "SELECT code, description, price FROM products ORDER BY code"
            ).fetchall()
        ]


def _normalize_product(row):
    code = str(row.get("code") or "").strip().upper()
    description = str(row.get("description") or "").strip()
    try:
        price = int(row.get("price") or 0)
    except (TypeError, ValueError):
        price = None
    return code, description, price


def import_products(source_db):
    source_path = Path(source_db).resolve()
    rows = _read_legacy_products(source_path)
    stats = {
        "source_db": str(source_path),
        "source_table": "products",
        "total_old": len(rows),
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
    }

    with app.app_context():
        for row in rows:
            code, description, price = _normalize_product(row)
            if not code or not description or price is None:
                stats["skipped"] += 1
                continue

            product = get_product_by_code(code)
            if product is None:
                db.session.add(NotaProduct(code=code, description=description, price=price))
                stats["created"] += 1
                continue

            if product.code != code or product.description != description or product.price != price:
                product.code = code
                product.description = description
                product.price = price
                stats["updated"] += 1
            else:
                stats["unchanged"] += 1

        db.session.commit()
        stats["total_erp"] = NotaProduct.query.count()

    return stats


def main():
    args = _parse_args()
    stats = import_products(args.source_db)
    print(f"Database lama: {stats['source_db']}")
    print(f"Tabel produk lama: {stats['source_table']}")
    print(f"Jumlah produk lama: {stats['total_old']}")
    print(f"Produk baru diimport: {stats['created']}")
    print(f"Produk diupdate: {stats['updated']}")
    print(f"Produk tidak berubah: {stats['unchanged']}")
    print(f"Produk dilewati: {stats['skipped']}")
    print(f"Total produk ERP sekarang: {stats['total_erp']}")


if __name__ == "__main__":
    main()
