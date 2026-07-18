from sqlalchemy import func

from database.db import db


def get_next_sort_order(model, filters=None, field_name="sort_order"):
    sort_field = getattr(model, field_name)
    query = db.session.query(func.max(sort_field))
    for filter_name, value in (filters or {}).items():
        query = query.filter(getattr(model, filter_name) == value)
    current_max = query.scalar() or 0
    return int(current_max) + 1
