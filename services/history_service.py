from database.db import db
from models.revision_history import RevisionHistory


def record_history(sales_order, actor_name, action, field_name=None, old_value=None, new_value=None, user=None, notes=None):
    history = RevisionHistory(
        sales_order=sales_order,
        user=user,
        actor_name=actor_name,
        action=action,
        field_name=field_name,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        notes=notes,
    )
    db.session.add(history)
    return history
