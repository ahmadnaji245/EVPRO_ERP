from sqlalchemy import extract

from models import Brand, SalesOrder
from utils.constants import normalize_production_status


PREFERRED_BRAND_FILTERS = ["Evpro", "FF Apparel", "RDR", "Armor"]
MONTH_OPTIONS = [
    (1, "Januari"),
    (2, "Februari"),
    (3, "Maret"),
    (4, "April"),
    (5, "Mei"),
    (6, "Juni"),
    (7, "Juli"),
    (8, "Agustus"),
    (9, "September"),
    (10, "Oktober"),
    (11, "November"),
    (12, "Desember"),
]


def _normalized_brand_filter(brand_name):
    brand_name = str(brand_name or "").strip()
    return brand_name if brand_name else None


def _parse_int_filter(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _orders_query(brand_name=None, month=None, year=None):
    query = SalesOrder.query.join(Brand).filter(SalesOrder.is_deleted.is_(False))
    brand_name = _normalized_brand_filter(brand_name)
    month = _parse_int_filter(month)
    year = _parse_int_filter(year)
    if brand_name:
        query = query.filter(Brand.name == brand_name)
    if year:
        query = query.filter(extract("year", SalesOrder.created_at) == year)
    if month and 1 <= month <= 12:
        query = query.filter(extract("month", SalesOrder.created_at) == month)
    return query


def brand_filter_options():
    brand_names = [brand.name for brand in Brand.query.order_by(Brand.name.asc()).all()]
    ordered = [brand for brand in PREFERRED_BRAND_FILTERS if brand in brand_names]
    ordered.extend(brand for brand in brand_names if brand not in ordered)
    return ordered


def year_filter_options():
    years = {
        order.created_at.year
        for order in SalesOrder.query.filter(SalesOrder.is_deleted.is_(False), SalesOrder.created_at.isnot(None)).all()
    }
    return sorted(years, reverse=True)


def report_summary(brand_name=None, month=None, year=None):
    orders = _orders_query(brand_name, month, year).all()
    total_size = sum(order.total_size for order in orders)
    total_point = sum(order.total_point for order in orders)
    return {
        "total_size": total_size,
        "total_point": total_point,
        "approval_pending": sum(1 for order in orders if order.approval_status == "pending"),
        "production_finish": sum(1 for order in orders if normalize_production_status(order.production_status) == "Selesai"),
    }


def period_summary(report):
    top_brand = None
    if report["groups"]:
        top_group = max(report["groups"], key=lambda group: group["total_order"])
        top_brand = top_group["brand"]
    return {
        "total_order": report["grand_total_order"],
        "total_point": report["grand_total_point"],
        "sales_order_count": sum(len(group["rows"]) for group in report["groups"]),
        "top_brand": top_brand or "-",
    }


def filter_title_parts(brand_name=None, month=None, year=None):
    parts = []
    month = _parse_int_filter(month)
    year = _parse_int_filter(year)
    if month and 1 <= month <= 12:
        month_name = dict(MONTH_OPTIONS)[month]
        parts.append(f"{month_name} {year}" if year else month_name)
    elif year:
        parts.append(str(year))
    brand_name = _normalized_brand_filter(brand_name)
    if brand_name:
        parts.append(brand_name)
    return parts


def production_report(brand_name=None, month=None, year=None):
    orders = (
        _orders_query(brand_name, month, year)
        .order_by(Brand.name.asc(), SalesOrder.created_at.desc(), SalesOrder.id.desc())
        .all()
    )
    groups = []
    brand_lookup = {}
    grand_total_order = 0
    grand_total_point = 0

    for order in orders:
        brand_name = order.brand.name if order.brand else "-"
        group = brand_lookup.get(brand_name)
        if not group:
            group = {
                "brand": brand_name,
                "rows": [],
                "total_order": 0,
                "total_point": 0,
            }
            brand_lookup[brand_name] = group
            groups.append(group)

        total_order = order.total_size
        total_point = order.total_point
        row = {
            "team_name": order.team_name,
            "brand": brand_name,
            "seller": order.seller_name if order.is_evpro_brand and order.seller_name else "-",
            "total_order": total_order,
            "point": total_point,
            "status": order.production_status_label,
            "created_at": order.created_at,
            "so_number": order.so_number,
        }
        group["rows"].append(row)
        group["total_order"] += total_order
        group["total_point"] += total_point
        grand_total_order += total_order
        grand_total_point += total_point

    return {
        "groups": groups,
        "grand_total_order": grand_total_order,
        "grand_total_point": grand_total_point,
    }
