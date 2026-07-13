from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from models import User
from services.petty_cash_service import (
    CATEGORY_TYPE_LABELS,
    INCOME_SOURCES,
    MONTH_OPTIONS,
    build_petty_cash_detail_pdf,
    build_petty_cash_pdf,
    categories,
    category_groups,
    create_expense,
    create_income,
    dashboard_data,
    ledger,
    month_expenses,
    set_category_active,
    transaction_year_options,
    upsert_category,
    void_transaction,
)
from utils.permissions import permission_required


finance_bp = Blueprint("finance", __name__, url_prefix="/keuangan")


@finance_bp.route("/")
@finance_bp.route("/kas-kecil")
@permission_required("finance.view")
def dashboard():
    return render_template(
        "finance/dashboard.html",
        data=dashboard_data(),
        income_sources=INCOME_SOURCES,
        type_labels=CATEGORY_TYPE_LABELS,
    )


@finance_bp.route("/kas-kecil/detail")
@permission_required("finance.view")
def detail():
    filters = _filters()
    pagination, running_rows, totals = ledger(filters, page=request.args.get("page", 1, type=int))
    return render_template(
        "finance/detail.html",
        pagination=pagination,
        running_rows=running_rows,
        totals=totals,
        filters=filters,
        categories=categories(active_only=True),
        groups=category_groups(active_only=True),
        month_options=MONTH_OPTIONS,
        year_options=transaction_year_options(),
        users=User.query.order_by(User.name.asc()).all(),
        today=date.today(),
        income_sources=INCOME_SOURCES,
    )


@finance_bp.route("/kas-kecil/pemasukan", methods=["GET", "POST"])
@permission_required("finance.manage")
def income_create():
    if request.method == "POST":
        try:
            trx = create_income(request.form, current_user, request.files.get("attachment"))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash(f"Pemasukan {trx.transaction_number} berhasil disimpan.", "success")
            return redirect(url_for("finance.detail"))
    return render_template("finance/income_form.html", income_sources={k: v for k, v in INCOME_SOURCES.items() if k != "NOTA_PAYMENT"}, today=date.today())


@finance_bp.route("/kas-kecil/pengeluaran", methods=["GET", "POST"])
@permission_required("finance.manage")
def expense_create():
    if request.method == "POST":
        try:
            trx = create_expense(request.form, current_user, request.files.get("attachment"))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash(f"Pengeluaran {trx.transaction_number} berhasil disimpan.", "success")
            return redirect(url_for("finance.detail"))
    return render_template("finance/expense_form.html", groups=category_groups(active_only=True), today=date.today())


@finance_bp.route("/kas-kecil/<int:transaction_id>/void", methods=["POST"])
@permission_required("finance.manage")
def transaction_void(transaction_id):
    try:
        void_transaction(transaction_id, request.form.get("void_reason"), current_user)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Transaksi berhasil dibatalkan.", "success")
    return redirect(request.referrer or url_for("finance.detail"))


@finance_bp.route("/pengeluaran-bulan-ini")
@permission_required("finance.view")
def current_month_expenses():
    return render_template("finance/month_expenses.html", data=month_expenses(), type_labels=CATEGORY_TYPE_LABELS)


@finance_bp.route("/kategori", methods=["GET", "POST"])
@permission_required("finance.manage")
def category_index():
    if request.method == "POST":
        try:
            upsert_category(request.form)
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Kategori berhasil disimpan.", "success")
        return redirect(url_for("finance.category_index"))
    return render_template("finance/categories.html", categories=categories(), type_labels=CATEGORY_TYPE_LABELS)


@finance_bp.route("/kategori/<int:category_id>/aktif", methods=["POST"])
@permission_required("finance.manage")
def category_activate(category_id):
    set_category_active(category_id, True)
    flash("Kategori diaktifkan.", "success")
    return redirect(url_for("finance.category_index"))


@finance_bp.route("/kategori/<int:category_id>/nonaktif", methods=["POST"])
@permission_required("finance.manage")
def category_deactivate(category_id):
    set_category_active(category_id, False)
    flash("Kategori dinonaktifkan.", "success")
    return redirect(url_for("finance.category_index"))


@finance_bp.route("/kas-kecil/pdf")
@permission_required("finance.view")
def report_pdf():
    pdf = build_petty_cash_pdf(_filters(), current_user)
    response = send_file(pdf, mimetype="application/pdf", as_attachment=False, download_name="laporan-kas-kecil.pdf")
    response.headers["Content-Disposition"] = 'inline; filename="laporan-kas-kecil.pdf"'
    return response


@finance_bp.route("/kas-kecil/detail/pdf")
@permission_required("finance.view")
def detail_report_pdf():
    pdf = build_petty_cash_detail_pdf(_filters(), current_user)
    response = send_file(pdf, mimetype="application/pdf", as_attachment=False, download_name="laporan-detail-kas-kecil.pdf")
    response.headers["Content-Disposition"] = 'inline; filename="laporan-detail-kas-kecil.pdf"'
    return response


def _filters():
    today = date.today()
    return {
        "month": request.args.get("month", str(today.month)).strip() or str(today.month),
        "year": request.args.get("year", str(today.year)).strip() or str(today.year),
        "transaction_type": request.args.get("transaction_type", "").strip(),
        "group_name": request.args.get("group_name", "").strip(),
        "category_id": request.args.get("category_id", "").strip(),
        "created_by": request.args.get("created_by", "").strip(),
        "status": request.args.get("status", "").strip(),
        "q": request.args.get("q", "").strip(),
    }
