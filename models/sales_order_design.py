from datetime import datetime

from database.db import db
from utils.constants import (
    has_long_sleeve_marker,
    long_sleeve_size_label,
    long_sleeve_type_label,
    normalize_size_key,
    size_group_name,
    sort_long_sleeve_rows,
    sort_players_by_size,
    sort_size_rows,
)


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
    def item_components(self):
        parts = [part.strip() for part in str(self.item_name or "").split("+")]
        return [part for part in parts if part]

    @property
    def primary_item_label(self):
        components = self.item_components
        return components[0] if components else (self.item_name or "Item")

    @property
    def secondary_item_label(self):
        components = self.item_components
        return components[1] if len(components) > 1 else None

    @property
    def has_secondary_item(self):
        return bool(self.secondary_item_label)

    @property
    def has_design_image(self):
        return bool(self.display_top_image_path or (self.has_secondary_item and self.bottom_image_path))

    @property
    def sorted_players(self):
        return sort_players_by_size(self.players)

    @property
    def size_recap(self):
        grouped_rows = {"Kids": {}, "Women": {}, "Reguler": {}}
        for index, player in enumerate(self.players):
            normalized = " ".join((player.size or "").split())
            display_size = long_sleeve_size_label(normalized) if has_long_sleeve_marker(normalized) else normalized
            key = normalize_size_key(display_size) or display_size.casefold()
            if not key or not display_size:
                continue
            group_name = size_group_name(display_size)
            rows = grouped_rows.setdefault(group_name, {})
            row = rows.setdefault(key, {"size": display_size, "qty": 0, "_first_index": index})
            row["qty"] += 1

        grouped = {}
        for group_name in ("Kids", "Women", "Reguler"):
            rows = sort_size_rows(grouped_rows.get(group_name, {}).values())
            if rows:
                grouped[group_name] = [{"size": row["size"], "qty": row["qty"]} for row in rows]

        return {"groups": grouped, "long_sleeve": []}

    @property
    def long_sleeve_recap(self):
        rows = {}
        for index, player in enumerate(self.players):
            if not has_long_sleeve_marker(player.size, player.notes):
                continue
            base_size = long_sleeve_size_label(player.size) or " ".join((player.size or "").split())
            sleeve_type = long_sleeve_type_label(player.size, player.notes)
            if not base_size or not sleeve_type:
                continue
            size_key = normalize_size_key(base_size) or base_size.casefold()
            key = (size_key, sleeve_type)
            row = rows.setdefault(
                key,
                {
                    "size": f"{base_size} {sleeve_type}",
                    "base_size": base_size,
                    "sleeve_type": sleeve_type,
                    "qty": 0,
                    "_first_index": index,
                },
            )
            row["qty"] += 1
        return [{"size": row["size"], "qty": row["qty"]} for row in sort_long_sleeve_rows(rows.values())]

    def size_setting_done(self, size):
        normalized = " ".join((size or "").split())
        return any(
            checklist.size == normalized and checklist.setting_done
            for checklist in self.size_checklists
        )
