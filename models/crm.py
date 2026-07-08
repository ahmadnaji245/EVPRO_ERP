from datetime import datetime

from database.db import db


CUSTOMER_SOURCES = ("Ahmad", "Reseller EVPRO", "Brand")
CUSTOMER_STATUSES = ("Baru", "Aktif", "Repeat", "Pasif")
FOLLOW_UP_STATUSES = (
    "Belum dihubungi",
    "Menunggu respon",
    "Closing",
    "Tidak jadi",
    "Follow up ulang",
)
LEAD_SOURCES = ("WhatsApp", "Instagram", "Facebook", "Website", "Lainnya")
LEAD_STATUSES = (
    "Baru masuk",
    "Sudah dibalas",
    "Tanya harga",
    "Menunggu desain",
    "Menunggu DP",
    "Follow up ulang",
    "Closing",
    "Tidak jadi",
)


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    whatsapp = db.Column(db.String(50), index=True)
    address = db.Column(db.Text)
    source = db.Column(db.String(50), nullable=False, default="Ahmad", index=True)
    source_name = db.Column(db.String(150))
    first_order_date = db.Column(db.Date, index=True)
    total_sales_orders = db.Column(db.Integer, nullable=False, default=0)
    total_notas = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default="Baru", index=True)
    character_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    sales_orders = db.relationship("SalesOrder", back_populates="crm_customer")
    notas = db.relationship("Nota", back_populates="crm_customer")
    follow_ups = db.relationship("FollowUp", back_populates="customer", cascade="all, delete-orphan")


class FollowUp(db.Model):
    __tablename__ = "follow_ups"

    id = db.Column(db.Integer, primary_key=True)
    follow_up_type = db.Column(db.String(20), nullable=False, default="Customer", index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True, index=True)
    follow_up_date = db.Column(db.Date, nullable=False, index=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    admin_name = db.Column(db.String(120))
    content = db.Column(db.Text, nullable=False)
    customer_response = db.Column(db.Text)
    status = db.Column(db.String(50), nullable=False, default="Belum dihubungi", index=True)
    next_follow_up_date = db.Column(db.Date, index=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = db.relationship("Customer", back_populates="follow_ups")
    lead = db.relationship("Lead", back_populates="follow_ups")
    admin = db.relationship("User")

    @property
    def target_name(self):
        if self.follow_up_type == "Lead" and self.lead:
            return self.lead.name
        if self.customer:
            return self.customer.name
        return "-"

    @property
    def target_source(self):
        if self.follow_up_type == "Lead" and self.lead:
            return self.lead.source
        if self.customer:
            return self.customer.source
        return "-"


class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    whatsapp = db.Column(db.String(50), index=True)
    source = db.Column(db.String(50), nullable=False, default="WhatsApp", index=True)
    source_detail = db.Column(db.String(150))
    need_type = db.Column(db.String(150))
    estimated_qty = db.Column(db.Integer)
    notes = db.Column(db.Text)
    status = db.Column(db.String(50), nullable=False, default="Baru masuk", index=True)
    next_follow_up_date = db.Column(db.Date, index=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    converted_customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), index=True)
    converted_so_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id"), index=True)

    assigned_user = db.relationship("User", foreign_keys=[assigned_to])
    converted_customer = db.relationship("Customer")
    converted_sales_order = db.relationship("SalesOrder", foreign_keys=[converted_so_id])
    follow_ups = db.relationship("FollowUp", back_populates="lead", cascade="all, delete-orphan")

    @property
    def is_converted(self):
        return bool(self.converted_customer_id or self.converted_so_id)


class WhatsAppTemplate(db.Model):
    __tablename__ = "whatsapp_templates"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
