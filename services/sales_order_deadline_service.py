from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from flask import current_app, has_app_context

from models.sales_order import DEADLINE_TYPE_FIXED, DEADLINE_TYPE_FLEXIBLE


def normalize_deadline_type(value, order=None):
    value = str(value or "").strip().casefold()
    if value in {DEADLINE_TYPE_FLEXIBLE, "fleksibel"}:
        return DEADLINE_TYPE_FLEXIBLE
    if value in {DEADLINE_TYPE_FIXED, "ditentukan", "deadline_ditentukan"}:
        return DEADLINE_TYPE_FIXED
    if order is not None:
        return order.normalized_deadline_type
    return DEADLINE_TYPE_FLEXIBLE


def approval_local_date(approved_at):
    if not approved_at:
        return None
    if isinstance(approved_at, date) and not isinstance(approved_at, datetime):
        return approved_at
    timezone_name = current_app.config.get("APP_TIMEZONE", "Asia/Jakarta") if has_app_context() else "Asia/Jakarta"
    local_timezone = ZoneInfo(timezone_name)
    if approved_at.tzinfo is None:
        approved_at = approved_at.replace(tzinfo=ZoneInfo("UTC"))
    return approved_at.astimezone(local_timezone).date()


def calculate_sales_order_deadline(order):
    if order.normalized_deadline_type == DEADLINE_TYPE_FIXED:
        return order.deadline
    approved_date = approval_local_date(order.approved_at)
    if not order.approved or not approved_date:
        return None
    production_days = int(order.production_days or 0)
    return approved_date + timedelta(days=production_days)


def apply_calculated_deadline(order):
    order.deadline = calculate_sales_order_deadline(order)
    sync_design_deadlines(order)
    return order.deadline


def sync_design_deadlines(order):
    for design in order.designs:
        design.production_days = order.production_days
        design.deadline = order.deadline


def reset_flexible_deadline_for_approval_reset(order):
    if order.normalized_deadline_type == DEADLINE_TYPE_FLEXIBLE:
        order.deadline = None
        sync_design_deadlines(order)
