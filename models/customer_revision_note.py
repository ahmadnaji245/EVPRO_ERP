from datetime import datetime

from database.db import db


class CustomerRevisionNote(db.Model):
    __tablename__ = "customer_revision_notes"

    id = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id"), nullable=False, index=True)
    customer_access_code = db.Column(db.String(80), nullable=False, index=True)
    note = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.String(30), nullable=False, default="customer")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    sales_order = db.relationship("SalesOrder", back_populates="customer_revisions")
