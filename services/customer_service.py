from datetime import datetime

from database.db import db
from models.customer_access import CustomerAccess


def find_by_access_code(access_code):
    access = CustomerAccess.query.filter_by(access_code=access_code, is_active=True).first()
    if access:
        access.last_access_at = datetime.utcnow()
        db.session.commit()
    return access
