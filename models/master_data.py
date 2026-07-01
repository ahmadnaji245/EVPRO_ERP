from datetime import datetime

from database.db import db


class MasterBase:
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_active(self):
        return self.status == "active"

    @is_active.setter
    def is_active(self, value):
        self.status = "active" if value else "inactive"


class MasterItem(MasterBase, db.Model):
    __tablename__ = "master_items"


class MasterMaterial(MasterBase, db.Model):
    __tablename__ = "master_materials"


class MasterPattern(MasterBase, db.Model):
    __tablename__ = "master_patterns"


class MasterInstruction(MasterBase, db.Model):
    __tablename__ = "master_instructions"
