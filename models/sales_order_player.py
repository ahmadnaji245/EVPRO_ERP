from datetime import datetime

from database.db import db


class SalesOrderPlayer(db.Model):
    __tablename__ = "sales_order_players"

    id = db.Column(db.Integer, primary_key=True)
    sales_order_design_id = db.Column(db.Integer, db.ForeignKey("sales_order_designs.id"), nullable=False, index=True)
    player_name = db.Column(db.String(150), nullable=False)
    player_number = db.Column(db.String(30))
    size = db.Column(db.String(30), nullable=False)
    notes = db.Column(db.Text)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    design = db.relationship("SalesOrderDesign", back_populates="players")
    checklist = db.relationship("ProductionChecklist", back_populates="player", uselist=False, cascade="all, delete-orphan")
    qc_checklist = db.relationship("QcChecklist", back_populates="player", uselist=False, cascade="all, delete-orphan")
