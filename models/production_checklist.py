from datetime import datetime

from database.db import db


class ProductionChecklist(db.Model):
    __tablename__ = "production_checklists"

    id = db.Column(db.Integer, primary_key=True)
    sales_order_player_id = db.Column(db.Integer, db.ForeignKey("sales_order_players.id"), nullable=False, unique=True)
    setting_done = db.Column(db.Boolean, nullable=False, default=False)
    setting_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    setting_at = db.Column(db.DateTime)
    setting_done_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    setting_done_by_name = db.Column(db.String(120))
    setting_done_at = db.Column(db.DateTime)
    qc_done = db.Column(db.Boolean, nullable=False, default=False)
    qc_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    qc_at = db.Column(db.DateTime)
    qc_done_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    qc_done_by_name = db.Column(db.String(120))
    qc_done_at = db.Column(db.DateTime)
    finish_done = db.Column(db.Boolean, nullable=False, default=False)
    finish_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    finish_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    player = db.relationship("SalesOrderPlayer", back_populates="checklist")
    setting_user = db.relationship("User", foreign_keys=[setting_user_id])
    setting_done_by_user = db.relationship("User", foreign_keys=[setting_done_by_user_id])
    qc_user = db.relationship("User", foreign_keys=[qc_user_id])
    qc_done_by_user = db.relationship("User", foreign_keys=[qc_done_by_user_id])
    finish_user = db.relationship("User", foreign_keys=[finish_user_id])
