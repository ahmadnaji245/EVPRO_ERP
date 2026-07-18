from datetime import datetime

from database.db import db


class PettyCashCategory(db.Model):
    __tablename__ = "petty_cash_categories"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("expense_category_groups.id"), index=True)
    group_name = db.Column(db.String(120), nullable=False, index=True)
    category_name = db.Column(db.String(150), nullable=False)
    category_code = db.Column(db.String(80), nullable=False, unique=True, index=True)
    category_type = db.Column(db.String(40), nullable=False, default="OPERATING_EXPENSE", index=True)
    is_operational_expense = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    transactions = db.relationship("PettyCashTransaction", back_populates="category")
    group = db.relationship("ExpenseCategoryGroup", back_populates="categories")


class ExpenseCategoryGroup(db.Model):
    __tablename__ = "expense_category_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    normalized_name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    code_prefix = db.Column(db.String(30), nullable=False, unique=True, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    categories = db.relationship("PettyCashCategory", back_populates="group")


class PettyCashTransaction(db.Model):
    __tablename__ = "petty_cash_transactions"

    id = db.Column(db.Integer, primary_key=True)
    transaction_number = db.Column(db.String(50), nullable=False, unique=True, index=True)
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    transaction_type = db.Column(db.String(3), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("petty_cash_categories.id"), index=True)
    amount = db.Column(db.Integer, nullable=False)
    source_type = db.Column(db.String(50), nullable=False, index=True)
    source_id = db.Column(db.Integer, index=True)
    reference_number = db.Column(db.String(120), index=True)
    recipient = db.Column(db.String(150))
    description = db.Column(db.Text)
    attachment_path = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_void = db.Column(db.Boolean, nullable=False, default=False, index=True)
    void_reason = db.Column(db.Text)
    voided_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    voided_at = db.Column(db.DateTime)

    category = db.relationship("PettyCashCategory", back_populates="transactions")
    creator = db.relationship("User", foreign_keys=[created_by])
    voider = db.relationship("User", foreign_keys=[voided_by])
    cash_advance = db.relationship("EmployeeCashAdvance", back_populates="transaction", uselist=False)
    allowance_reserve = db.relationship("AllowanceReserve", back_populates="transaction", uselist=False)


class EmployeeCashAdvance(db.Model):
    __tablename__ = "employee_cash_advances"

    id = db.Column(db.Integer, primary_key=True)
    petty_cash_transaction_id = db.Column(db.Integer, db.ForeignKey("petty_cash_transactions.id"), nullable=False, unique=True)
    employee_name = db.Column(db.String(150), nullable=False)
    advance_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Belum Dipotong", index=True)
    settlement_date = db.Column(db.Date)
    settlement_method = db.Column(db.String(80))
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    transaction = db.relationship("PettyCashTransaction", back_populates="cash_advance")
    creator = db.relationship("User")


class AllowanceReserve(db.Model):
    __tablename__ = "allowance_reserves"

    id = db.Column(db.Integer, primary_key=True)
    petty_cash_transaction_id = db.Column(db.Integer, db.ForeignKey("petty_cash_transactions.id"), nullable=False, unique=True)
    allowance_type = db.Column(db.String(120), nullable=False)
    allowance_period = db.Column(db.String(80))
    destination_account = db.Column(db.String(150))
    amount = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    transaction = db.relationship("PettyCashTransaction", back_populates="allowance_reserve")


class FinancialAuditLog(db.Model):
    __tablename__ = "financial_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(80), nullable=False, index=True)
    entity_id = db.Column(db.Integer, index=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    creator = db.relationship("User")
