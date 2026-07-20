from datetime import datetime

from sqlalchemy import event, inspect

from database.db import db
from utils.constants import normalize_production_status


class SalesOrder(db.Model):
    __tablename__ = "sales_orders"

    id = db.Column(db.Integer, primary_key=True)
    so_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    tracking_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    team_name = db.Column(db.String(150), nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=False)
    seller_name = db.Column(db.String(150))
    customer_code = db.Column(db.String(50), nullable=False, index=True)
    access_code = db.Column(db.String(80), unique=True, nullable=False, index=True)
    material = db.Column(db.String(120))
    pattern = db.Column(db.String(80))
    grade = db.Column(db.String(20))
    production_days = db.Column(db.Integer, nullable=False, default=7)
    deadline = db.Column(db.Date)
    instructions = db.Column(db.Text)
    notes = db.Column(db.Text)
    approval_status = db.Column(db.String(30), nullable=False, default="pending")
    approved_by = db.Column(db.String(120))
    approved_source = db.Column(db.String(30))
    approved_at = db.Column(db.DateTime)
    customer_portal_status = db.Column(db.String(50), nullable=False, default="Approval Customer")
    revision_reason_admin = db.Column(db.Text)
    revision_time = db.Column(db.DateTime)
    revision_by_admin_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    production_status = db.Column(db.String(40), nullable=False, default="Approval Customer")
    production_status_updated_at = db.Column(db.DateTime)
    setting_by_name = db.Column(db.String(120))
    production_vendor = db.Column(db.String(80), index=True)
    production_vendor_deadline = db.Column(db.Date)
    production_assigned_at = db.Column(db.DateTime)
    printing_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    printing_started_at = db.Column(db.DateTime)
    printing_started_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    warehouse_received_at = db.Column(db.DateTime)
    shortage_note = db.Column(db.Text)
    qc_note = db.Column(db.Text)
    tanggal_finish_produksi = db.Column(db.DateTime)
    tanggal_pengambilan = db.Column(db.Date)
    diambil_oleh = db.Column(db.String(150))
    catatan_pengambilan = db.Column(db.Text)
    serah_terima_admin_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    is_deleted = db.Column(db.Boolean, nullable=False, default=False, index=True)
    deleted_at = db.Column(db.DateTime)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    crm_customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    brand = db.relationship("Brand", back_populates="sales_orders")
    created_by = db.relationship("User", back_populates="sales_orders", foreign_keys=[created_by_id])
    printing_started_user = db.relationship("User", foreign_keys=[printing_started_by])
    crm_customer = db.relationship("Customer", back_populates="sales_orders")
    serah_terima_admin = db.relationship("User", foreign_keys=[serah_terima_admin_id])
    designs = db.relationship("SalesOrderDesign", back_populates="sales_order", cascade="all, delete-orphan")
    revision_histories = db.relationship("RevisionHistory", back_populates="sales_order", cascade="all, delete-orphan")
    customer_revisions = db.relationship("CustomerRevisionNote", back_populates="sales_order", cascade="all, delete-orphan")
    customer_access = db.relationship("CustomerAccess", back_populates="sales_order", uselist=False, cascade="all, delete-orphan")
    qc_checklists = db.relationship("QcChecklist", back_populates="sales_order", cascade="all, delete-orphan")
    production_photos = db.relationship(
        "SalesOrderProductionPhoto",
        back_populates="sales_order",
        cascade="all, delete-orphan",
        order_by="SalesOrderProductionPhoto.sort_order",
    )

    @property
    def approved(self):
        return self.approval_status == "approved"

    @approved.setter
    def approved(self, value):
        self.approval_status = "approved" if value else "pending"

    @property
    def total_size(self):
        return sum(design.total_size for design in self.designs)

    @property
    def total_point(self):
        return self.total_size * (self.brand.point_per_size if self.brand else 1)

    @property
    def production_status_label(self):
        if self.approval_status != "approved":
            return "Approval Customer"
        return normalize_production_status(self.production_status)

    @property
    def is_evpro_brand(self):
        if not self.brand:
            return False
        return str(self.brand.name or "").strip().casefold() == "evpro" or str(self.brand.code or "").strip().casefold() == "evpro"

    @property
    def portal_status_label(self):
        if self.approval_status != "approved":
            return "Approval Customer"
        return normalize_production_status(self.customer_portal_status or self.production_status or "Approval Customer")


@event.listens_for(SalesOrder, "before_update")
def _prevent_tracking_code_change(mapper, connection, target):
    history = inspect(target).attrs.tracking_code.history
    if history.has_changes() and history.deleted and history.deleted[0]:
        raise ValueError("Tracking code tidak boleh diubah setelah dibuat.")
