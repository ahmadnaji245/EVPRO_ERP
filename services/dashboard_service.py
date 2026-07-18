import calendar
from datetime import date

from models import ProductionChecklist, SalesOrderDesign, SalesOrderPlayer, Setting
from models.sales_order import SalesOrder
from utils.constants import normalize_production_status

SETTING_POINT_CHART_COLORS = [
    "#DC3545",
    "#0D6EFD",
    "#198754",
    "#FD7E14",
    "#6F42C1",
    "#20C997",
    "#FFC107",
    "#6C757D",
    "#E83E8C",
    "#6610F2",
]

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

DAY_NAMES = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def dashboard_stats():
    today = date.today()
    orders = SalesOrder.query.filter_by(is_deleted=False).all()
    today_orders = [order for order in orders if order.created_at.date() == today]
    month_orders = [order for order in orders if order.created_at.year == today.year and order.created_at.month == today.month]
    total_size = sum(order.total_size for order in orders)
    total_point = sum(order.total_point for order in orders)
    return {
        "today_point": sum(order.total_point for order in today_orders),
        "month_point": sum(order.total_point for order in month_orders),
        "total_size": total_size,
        "total_point": total_point,
        "approval_pending": sum(1 for order in orders if order.approval_status == "pending"),
        "approval_done": sum(1 for order in orders if order.approval_status == "approved"),
        "production_running": sum(1 for order in orders if normalize_production_status(order.production_status) != "Finish"),
        "production_finish": sum(1 for order in orders if normalize_production_status(order.production_status) == "Finish"),
    }


def monthly_point_chart():
    today = date.today()
    labels = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    values = [0] * 12
    for order in SalesOrder.query.filter_by(is_deleted=False).all():
        values[order.created_at.month - 1] += order.total_point
    target = _monthly_target_value()
    current_month_point = values[today.month - 1]
    return {
        "labels": labels,
        "values": values,
        "targets": [target] * 12,
        "target": target,
        "current_month_point": current_month_point,
        "remaining": max(target - current_month_point, 0),
        "percentage": (current_month_point / target * 100) if target else 0,
    }


def _monthly_target_value():
    target = Setting.query.filter_by(key="monthly_target").first()
    try:
        return float(target.value) if target and target.value else 0
    except (TypeError, ValueError):
        return 0


def _checklist_setting_at(checklist):
    return checklist.setting_done_at or checklist.setting_at


def _checklist_setting_user_id(checklist):
    return checklist.setting_done_by_user_id or checklist.setting_user_id


def _checklist_setting_user_name(checklist):
    if checklist.setting_done_by_name:
        return checklist.setting_done_by_name
    if checklist.setting_done_by_user:
        return checklist.setting_done_by_user.name
    if checklist.setting_user:
        return checklist.setting_user.name
    return "User Tidak Diketahui"


def _player_setting_point(player):
    order = player.design.sales_order if player and player.design else None
    return order.brand.point_per_size if order and order.brand else 1


def monthly_setting_point_progress(month=None, year=None):
    today = date.today()
    month = _valid_month(month, today.month)
    year = _valid_year(year, today.year)
    users = {}

    for checklist in _setting_checklists():
        setting_at = _checklist_setting_at(checklist)
        if not setting_at or setting_at.year != year or setting_at.month != month:
            continue
        user_id = _checklist_setting_user_id(checklist) or f"name:{_checklist_setting_user_name(checklist)}"
        row = users.setdefault(
            user_id,
            {
                "user_id": user_id,
                "name": _checklist_setting_user_name(checklist),
                "total_point": 0,
            },
        )
        row["total_point"] += _player_setting_point(checklist.player)

    rows = sorted(users.values(), key=lambda row: (-row["total_point"], row["name"]))
    for index, row in enumerate(rows):
        row["rank"] = index + 1
        row["color"] = SETTING_POINT_CHART_COLORS[index % len(SETTING_POINT_CHART_COLORS)]

    total_point = sum(row["total_point"] for row in rows)
    top_user = rows[0] if rows else None
    return {
        "total_point": total_point,
        "top_user": top_user,
        "rows": rows,
        "labels": [row["name"] for row in rows],
        "values": [row["total_point"] for row in rows],
        "colors": [row["color"] for row in rows],
    }


def daily_setting_point_chart(month=None, year=None):
    today = date.today()
    month = _valid_month(month, today.month)
    year = _valid_year(year, today.year)
    days_in_month = calendar.monthrange(year, month)[1]
    daily_rows = {}
    month_so_ids = set()

    for day in range(1, days_in_month + 1):
        current = date(year, month, day)
        daily_rows[day] = {
            "date": current,
            "label": f"{day:02d} {MONTH_OPTIONS[month - 1][1][:3]}",
            "day_name": DAY_NAMES[current.weekday()],
            "total_point": 0,
            "so_ids": set(),
        }

    for checklist in _setting_checklists():
        setting_at = _checklist_setting_at(checklist)
        if not setting_at or setting_at.year != year or setting_at.month != month:
            continue
        order = checklist.player.design.sales_order if checklist.player and checklist.player.design else None
        day_row = daily_rows[setting_at.day]
        day_row["total_point"] += _player_setting_point(checklist.player)
        if order:
            day_row["so_ids"].add(order.id)
            month_so_ids.add(order.id)

    rows = []
    for day in range(1, days_in_month + 1):
        row = daily_rows[day]
        rows.append(
            {
                "date": row["date"],
                "label": row["label"],
                "day_name": row["day_name"],
                "total_point": row["total_point"],
                "so_count": len(row["so_ids"]),
            }
        )

    total_point = sum(row["total_point"] for row in rows)
    active_rows = [row for row in rows if row["total_point"] > 0]
    busiest_day = max(rows, key=lambda row: (row["total_point"], -row["date"].day)) if rows else None
    weekday_rows = []
    for weekday_index, day_name in enumerate(DAY_NAMES):
        weekday_days = [row for row in rows if row["date"].weekday() == weekday_index]
        total_weekday_point = sum(row["total_point"] for row in weekday_days)
        weekday_rows.append(
            {
                "day_name": day_name,
                "average_point": (total_weekday_point / len(weekday_days)) if weekday_days else 0,
            }
        )

    return {
        "month": month,
        "year": year,
        "month_options": MONTH_OPTIONS,
        "year_options": _year_options(year),
        "labels": [row["label"] for row in rows],
        "values": [row["total_point"] for row in rows],
        "tooltips": [
            {
                "date": _format_indonesian_date(row["date"]),
                "day_name": row["day_name"],
                "total_point": row["total_point"],
                "so_count": row["so_count"],
            }
            for row in rows
        ],
        "summary": {
            "total_point": total_point,
            "active_day_average": (total_point / len(active_rows)) if active_rows else 0,
            "busiest_day": _format_busiest_day(busiest_day) if busiest_day and busiest_day["total_point"] > 0 else "-",
            "total_so": len(month_so_ids),
        },
        "weekday_averages": weekday_rows,
    }


def _setting_checklists():
    return (
        ProductionChecklist.query.join(SalesOrderPlayer)
        .join(SalesOrderDesign)
        .join(SalesOrder)
        .filter(
            ProductionChecklist.setting_done.is_(True),
            SalesOrder.is_deleted.is_(False),
            SalesOrder.deleted_at.is_(None),
        )
        .all()
    )


def _valid_month(value, default):
    try:
        month = int(value)
    except (TypeError, ValueError):
        return default
    return month if 1 <= month <= 12 else default


def _valid_year(value, default):
    try:
        year = int(value)
    except (TypeError, ValueError):
        return default
    return year if 2000 <= year <= 2100 else default


def _year_options(selected_year):
    today = date.today()
    start_year = min(2020, selected_year, today.year)
    end_year = max(today.year + 1, selected_year)
    return list(range(end_year, start_year - 1, -1))


def _format_indonesian_date(value):
    return f"{value.day} {MONTH_OPTIONS[value.month - 1][1]} {value.year}"


def _format_busiest_day(row):
    return f"{row['day_name']}, {_format_indonesian_date(row['date'])}"
