from datetime import datetime

from database.db import db


class RevisionHistory(db.Model):
    __tablename__ = "revision_histories"

    id = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    actor_name = db.Column(db.String(120), nullable=False)
    action = db.Column(db.String(120), nullable=False)
    field_name = db.Column(db.String(120))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    sales_order = db.relationship("SalesOrder", back_populates="revision_histories")
    user = db.relationship("User", back_populates="revision_histories")
