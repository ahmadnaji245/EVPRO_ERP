from datetime import datetime

from database.db import db


class SalesOrderAttachment(db.Model):
    __tablename__ = "sales_order_attachments"

    id = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id"), nullable=False, index=True)
    file_path = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(150))
    note = db.Column(db.Text)
    original_filename = db.Column(db.String(255))
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_by_name = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    sales_order = db.relationship("SalesOrder", back_populates="attachments")
    created_by = db.relationship("User")
