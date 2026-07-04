from datetime import datetime

from database.db import db


class SalesOrderProductionPhoto(db.Model):
    __tablename__ = "sales_order_production_photos"

    id = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id"), nullable=False, index=True)
    file_path = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255))
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    sales_order = db.relationship("SalesOrder", back_populates="production_photos")
    uploaded_by = db.relationship("User")
