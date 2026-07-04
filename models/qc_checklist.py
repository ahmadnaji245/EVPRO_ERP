from datetime import datetime

from database.db import db


class QcChecklist(db.Model):
    __tablename__ = "qc_checklists"

    id = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id"), nullable=False, index=True)
    sales_order_player_id = db.Column(db.Integer, db.ForeignKey("sales_order_players.id"), nullable=False, unique=True, index=True)
    qc_jersey = db.Column(db.Boolean, nullable=False, default=False)
    cek_jersey = db.Column(db.Boolean, nullable=False, default=False)
    qc_celana = db.Column(db.Boolean, nullable=False, default=False)
    cek_celana = db.Column(db.Boolean, nullable=False, default=False)
    qc_data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    sales_order = db.relationship("SalesOrder", back_populates="qc_checklists")
    player = db.relationship("SalesOrderPlayer", back_populates="qc_checklist")
