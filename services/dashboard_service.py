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
        "production_running": sum(1 for order in orders if normalize_production_status(order.production_status) != "Selesai"),
        "production_finish": sum(1 for order in orders if normalize_production_status(order.production_status) == "Selesai"),
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


def monthly_setting_point_progress():
    today = date.today()
    users = {}

    checklists = (
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
    for checklist in checklists:
        setting_at = _checklist_setting_at(checklist)
        if not setting_at or setting_at.year != today.year or setting_at.month != today.month:
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
