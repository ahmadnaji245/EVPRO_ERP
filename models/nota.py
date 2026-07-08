from datetime import datetime

from database.db import db


class NotaCustomer(db.Model):
    __tablename__ = "nota_customers"

    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    team_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    brand = db.relationship("Brand")
    notas = db.relationship("Nota", back_populates="customer")


class NotaProduct(db.Model):
    __tablename__ = "nota_products"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Nota(db.Model):
    __tablename__ = "notas"

    id = db.Column(db.Integer, primary_key=True)
    nota_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=False, index=True)
    order_date = db.Column(db.Date, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("nota_customers.id"), nullable=False, index=True)
    team_name = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Belum DP", index=True)
    notes = db.Column(db.Text)
    so_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id"), nullable=True, unique=True, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    crm_customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    brand = db.relationship("Brand")
    customer = db.relationship("NotaCustomer", back_populates="notas")
    sales_order = db.relationship("SalesOrder")
    created_by = db.relationship("User")
    crm_customer = db.relationship("Customer", back_populates="notas")
    items = db.relationship("NotaItem", back_populates="nota", cascade="all, delete-orphan")
    payments = db.relationship("NotaPayment", back_populates="nota", cascade="all, delete-orphan")

    @property
    def invoice_number(self):
        return self.nota_number

    @property
    def total(self):
        return sum(item.subtotal for item in self.items)

    @property
    def paid(self):
        return sum(payment.amount for payment in self.payments)

    @property
    def remaining(self):
        return max(self.total - self.paid, 0)


class NotaItem(db.Model):
    __tablename__ = "nota_items"

    id = db.Column(db.Integer, primary_key=True)
    nota_id = db.Column(db.Integer, db.ForeignKey("notas.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("nota_products.id"), nullable=False, index=True)
    product_code = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Integer, nullable=False, default=0)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    subtotal = db.Column(db.Integer, nullable=False, default=0)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    nota = db.relationship("Nota", back_populates="items")
    product = db.relationship("NotaProduct")


class NotaPayment(db.Model):
    __tablename__ = "nota_payments"

    id = db.Column(db.Integer, primary_key=True)
    nota_id = db.Column(db.Integer, db.ForeignKey("notas.id"), nullable=False, index=True)
    payment_date = db.Column(db.Date, nullable=False, index=True)
    amount = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    nota = db.relationship("Nota", back_populates="payments")
