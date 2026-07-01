from datetime import datetime

from database.db import db


class SalesOrderDesign(db.Model):
    __tablename__ = "sales_order_designs"

    id = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id"), nullable=False, index=True)
    design_name = db.Column(db.String(150), nullable=False)
    item_name = db.Column(db.String(120), nullable=False)
    material = db.Column(db.String(120))
    pattern = db.Column(db.String(80))
    grade = db.Column(db.String(20))
    production_days = db.Column(db.Integer, nullable=False, default=7)
    deadline = db.Column(db.Date)
    instruction = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    top_image_path = db.Column(db.String(255))
    bottom_image_path = db.Column(db.String(255))
    top_notes = db.Column(db.Text)
    bottom_notes = db.Column(db.Text)
    notes = db.Column(db.Text)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    sales_order = db.relationship("SalesOrder", back_populates="designs")
    players = db.relationship("SalesOrderPlayer", back_populates="design", cascade="all, delete-orphan")
    size_checklists = db.relationship("ProductionSizeChecklist", back_populates="design", cascade="all, delete-orphan")

    @property
    def total_size(self):
        return len(self.players)

    @property
    def display_top_image_path(self):
        return self.top_image_path or self.image_path

    @property
    def display_top_notes(self):
        return self.top_notes or self.instruction

    @property
    def size_recap(self):
        groups = {
            "Kids": ["XS Kids", "S Kids", "M Kids", "L Kids", "XL Kids", "XXL Kids"],
            "Women": ["XS Women", "S Women", "M Women", "L Women", "XL Women", "XXL Women", "3XL Women"],
            "Reguler": ["S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL"],
        }
        long_sleeve_order = [
            "XS Kids Lengan Panjang",
            "S Kids Lengan Panjang",
            "M Kids Lengan Panjang",
            "L Kids Lengan Panjang",
            "XL Kids Lengan Panjang",
            "XXL Kids Lengan Panjang",
            "XS Women Lengan Panjang",
            "S Women Lengan Panjang",
            "M Women Lengan Panjang",
            "L Women Lengan Panjang",
            "XL Women Lengan Panjang",
            "XXL Women Lengan Panjang",
            "3XL Women Lengan Panjang",
            "S Lengan Panjang",
            "M Lengan Panjang",
            "L Lengan Panjang",
            "XL Lengan Panjang",
            "XXL Lengan Panjang",
            "3XL Lengan Panjang",
            "4XL Lengan Panjang",
            "5XL Lengan Panjang",
        ]
        counts = {}
        labels = {}
        for player in self.players:
            normalized = " ".join((player.size or "").split())
            key = normalized.lower()
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
            labels.setdefault(key, normalized)

        grouped = {}
        for group_name, sizes in groups.items():
            rows = []
            for size in sizes:
                qty = counts.get(size.lower(), 0)
                if qty:
                    rows.append({"size": size, "qty": qty})
            if rows:
                grouped[group_name] = rows

        known_long_sleeve = {size.lower() for size in long_sleeve_order}
        long_sleeve_rows = []
        for size in long_sleeve_order:
            qty = counts.get(size.lower(), 0)
            if qty:
                long_sleeve_rows.append({"size": size, "qty": qty})
        for key, qty in counts.items():
            if "lengan panjang" in key and key not in known_long_sleeve:
                long_sleeve_rows.append({"size": labels[key], "qty": qty})

        return {"groups": grouped, "long_sleeve": long_sleeve_rows}

    def size_setting_done(self, size):
        normalized = " ".join((size or "").split())
        return any(
            checklist.size == normalized and checklist.setting_done
            for checklist in self.size_checklists
        )
