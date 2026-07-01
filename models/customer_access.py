from datetime import datetime

from database.db import db


class CustomerAccess(db.Model):
    __tablename__ = "customer_access"

    id = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id"), nullable=False, unique=True)
    access_code = db.Column(db.String(80), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(150))
    customer_phone = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_access_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    sales_order = db.relationship("SalesOrder", back_populates="customer_access")
