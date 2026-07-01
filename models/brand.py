from datetime import datetime

from database.db import db


class Brand(db.Model):
    __tablename__ = "brands"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    logo_path = db.Column(db.String(255))
    color = db.Column(db.String(20), nullable=False, default="#c5162e")
    point_per_size = db.Column(db.Float, nullable=False, default=1.0)
    status = db.Column(db.String(20), nullable=False, default="active")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    sales_orders = db.relationship("SalesOrder", back_populates="brand")

    def badge_label(self):
        return self.code.upper()

    @property
    def is_active(self):
        return self.status == "active"

    @is_active.setter
    def is_active(self, value):
        self.status = "active" if value else "inactive"

    @property
    def note(self):
        return self.notes

    @note.setter
    def note(self, value):
        self.notes = value
