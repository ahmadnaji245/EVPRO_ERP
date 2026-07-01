from datetime import datetime

from database.db import db


class ProductionSizeChecklist(db.Model):
    __tablename__ = "production_size_checklists"

    id = db.Column(db.Integer, primary_key=True)
    sales_order_design_id = db.Column(db.Integer, db.ForeignKey("sales_order_designs.id"), nullable=False, index=True)
    size = db.Column(db.String(80), nullable=False)
    setting_done = db.Column(db.Boolean, nullable=False, default=False)
    setting_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    setting_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    design = db.relationship("SalesOrderDesign", back_populates="size_checklists")
    setting_user = db.relationship("User", foreign_keys=[setting_user_id])

    __table_args__ = (
        db.UniqueConstraint("sales_order_design_id", "size", name="uq_production_size_checklists_design_size"),
    )
