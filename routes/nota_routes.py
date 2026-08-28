from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for

from flask_login import current_user

from utils.permissions import permission_required
from services.nota_service import (
    MONTH_OPTIONS,
    NOTA_STATUSES,
    add_payment,
    brand_report_rows,
    build_nota_report_pdf,
    calculate_invoice_status,
    create_nota,
    dashboard_stats,
    delete_nota,
    delete_product,
    display_nota_number,
    evpro_seller_report_rows,
    format_so_number_for_invoice,
    form_data_from_sales_order,
    get_nota,
    get_invoice_brand,
    get_nota_by_so_id,
    get_payment,
    income_payments,
    income_summary,
    invoice_export_rows,
    item_rows_from_sales_order,
    item_rows_for_form,
    list_invoice_brand_options,
    list_brands_for_form,
    list_customers_as_dicts,
    list_notas,
    list_products,
    list_products_as_dicts,
    monthly_revenue,
    nota_rows,
    posted_item_rows,
    receivables,
    report_nota_rows,
    report_year_options,
    top_customers,
    totals,
    update_payment,
    update_nota,
    upsert_product,
    validate_nota_form,
    void_payment,
    workbook_response,
    yearly_revenue,
)
from services.nota_pdf_ff_apparel_service import build_ff_apparel_pdf
from services.nota_pdf_service import build_customer_invoice_pdf, build_internal_note_pdf
from services.sales_order_service import get_sales_order
from utils.helpers import nota_pdf_download_name


nota_bp = Blueprint("nota", __name__, url_prefix="/nota")


def _admin_required():
    if not current_user.is_admin:
        abort(403)


def _form_context(**kwargs):
    nota = kwargs.get("nota")
    form = kwargs.get("form") or {}
    selected_brand_id = form.get("brand_id") or (nota.brand_id if nota else None)
    context = {
        "statuses": NOTA_STATUSES,
        "brands": list_brands_for_form(selected_brand_id),
        "products": list_products_as_dicts(),
        "customers": list_customers_as_dicts(),
        "today": date.today().isoformat(),
    }
    context.update(kwargs)
    return context


def _brand_filter():
    return request.args.get("brand_id", "").strip()


def _report_period_filter():
    month = request.args.get("month", "").strip()
    year = request.args.get("year", "").strip()
    month = int(month) if month.isdigit() and 1 <= int(month) <= 12 else None
    year = int(year) if year.isdigit() and 2000 <= int(year) <= 2100 else None
    return year, month


def _report_query(brand=None, year=None, month=None):
    query = {}
    if brand:
        query["brand_id"] = brand
    if year:
        query["year"] = year
    if month:
        query["month"] = month
    return query


def _brand_filter_label(brand_id):
    if not str(brand_id or "").isdigit():
        return "Semua Brand"
    brand = next((item for item in list_invoice_brand_options() if item.id == int(brand_id)), None)
    return brand.name if brand else "Brand Terpilih"


def _show_evpro_seller_report(brand_id):
    if not str(brand_id or "").isdigit():
        return True
    brand = next((item for item in list_invoice_brand_options() if item.id == int(brand_id)), None)
    if not brand:
        return False
    return str(brand.name or "").strip().casefold() == "evpro" or str(brand.code or "").strip().casefold() == "evpro"


@nota_bp.route("/dashboard")
@permission_required("nota.view")
def dashboard():
    brand_id = _brand_filter()
    return render_template(
        "nota/dashboard.html",
        stats=dashboard_stats(brand_id or None),
        monthly=monthly_revenue(brand_id or None),
        yearly=yearly_revenue(brand_id or None),
        brands=list_invoice_brand_options(),
        active_brand_id=brand_id,
    )


@nota_bp.route("/")
@permission_required("nota.view")
def index():
    search = {
        "q": request.args.get("q", "").strip(),
        "status": request.args.get("status", "").strip(),
        "brand_id": _brand_filter(),
    }
    return render_template(
        "nota/index.html",
        notas=list_notas(search),
        statuses=NOTA_STATUSES,
        brands=list_invoice_brand_options(),
        calculate_invoice_status=calculate_invoice_status,
        format_so_number_for_invoice=format_so_number_for_invoice,
        search=search["q"],
        active_status=search["status"],
        active_brand_id=search["brand_id"],
    )


@nota_bp.route("/produk", methods=["GET", "POST"])
@permission_required("nota.manage")
def products():
    if request.method == "POST":
        try:
            upsert_product(request.form)
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Produk berhasil disimpan.", "success")
        return redirect(url_for("nota.products"))
    return render_template("nota/products.html", products=list_products())


@nota_bp.route("/produk/delete/<int:product_id>")
@permission_required("nota.manage")
def delete_product_view(product_id):
    delete_product(product_id)
    flash("Produk berhasil dihapus.", "success")
    return redirect(url_for("nota.products"))


@nota_bp.route("/<int:nota_id>/delete", methods=["POST"])
@permission_required("nota.manage")
def delete(nota_id):
    nota = get_nota(nota_id)
    delete_nota(nota)
    flash("Nota berhasil dihapus.", "success")
    return redirect(url_for("nota.index"))


@nota_bp.route("/laporan")
@permission_required("nota.view")
def reports():
    brand_id = _brand_filter()
    year, month = _report_period_filter()
    return render_template(
        "nota/reports/index.html",
        stats=dashboard_stats(brand_id or None, year, month),
        brand_reports=brand_report_rows(brand_id or None, year, month),
        evpro_seller_reports=evpro_seller_report_rows(brand_id or None, year, month),
        brands=list_invoice_brand_options(),
        active_brand_id=brand_id,
        active_year=year,
        active_month=month,
        month_options=MONTH_OPTIONS,
        year_options=report_year_options(year),
        report_query=_report_query(brand_id, year, month),
        show_evpro_seller_report=_show_evpro_seller_report(brand_id),
    )


@nota_bp.route("/laporan/pdf")
@permission_required("nota.view")
def report_pdf():
    brand_id = _brand_filter()
    year, month = _report_period_filter()
    brand_rows = brand_report_rows(brand_id or None, year, month)
    seller_rows = evpro_seller_report_rows(brand_id or None, year, month)
    stats = dashboard_stats(brand_id or None, year, month)
    pdf = build_nota_report_pdf(
        brand_rows,
        seller_rows,
        stats,
        {
            "brand": _brand_filter_label(brand_id),
            "month": dict(MONTH_OPTIONS).get(month) if month else None,
            "year": year,
            "show_evpro_sellers": _show_evpro_seller_report(brand_id),
        },
    )
    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=False,
        download_name="laporan-nota.pdf",
    )


@nota_bp.route("/laporan/customer")
@permission_required("nota.view")
def customer_report():
    brand_id = _brand_filter()
    year, month = _report_period_filter()
    return render_template(
        "nota/reports/customers.html",
        customers=top_customers(brand_id or None, year, month),
        brands=list_invoice_brand_options(),
        active_brand_id=brand_id,
        active_year=year,
        active_month=month,
        month_options=MONTH_OPTIONS,
        year_options=report_year_options(year),
    )


@nota_bp.route("/piutang")
@permission_required("nota.view")
def receivables_page():
    brand_id = _brand_filter()
    status = request.args.get("status", "").strip()
    return render_template(
        "nota/reports/receivables.html",
        invoices=receivables(brand_id or None, status or None),
        statuses=NOTA_STATUSES,
        brands=list_invoice_brand_options(),
        active_brand_id=brand_id,
        active_status=status,
    )


@nota_bp.route("/pemasukan")
@permission_required("nota.view")
def income_page():
    brand_id = _brand_filter()
    return render_template(
        "nota/reports/income.html",
        payments=income_payments(brand_id or None),
        summary=income_summary(brand_id or None),
        brands=list_invoice_brand_options(),
        active_brand_id=brand_id,
    )


@nota_bp.route("/export/nota")
@permission_required("nota.view")
def export_invoices():
    year, month = _report_period_filter()
    rows = invoice_export_rows(report_nota_rows(_brand_filter() or None, year, month))
    workbook = workbook_response(
        "Semua Nota",
        ["Nomor Nota", "Tanggal", "Brand", "Customer", "Tim", "Total Nota", "Sudah Dibayar", "Sisa Piutang", "Status"],
        rows,
    )
    return _excel_file(workbook, "semua-nota.xlsx")


@nota_bp.route("/export/piutang")
@permission_required("nota.view")
def export_receivables():
    year, month = _report_period_filter()
    rows = invoice_export_rows(receivables(_brand_filter() or None, year=year, month=month))
    workbook = workbook_response(
        "Piutang",
        ["Nomor Nota", "Tanggal", "Brand", "Customer", "Tim", "Total Nota", "Sudah Dibayar", "Sisa Piutang", "Status"],
        rows,
    )
    return _excel_file(workbook, "piutang.xlsx")


@nota_bp.route("/export/omset-bulanan")
@permission_required("nota.view")
def export_monthly_revenue():
    year, month = _report_period_filter()
    rows = [[row.month, row.total] for row in monthly_revenue(_brand_filter() or None, year, month)]
    workbook = workbook_response("Omset Bulanan", ["Bulan", "Omset"], rows)
    return _excel_file(workbook, "omset-bulanan.xlsx")


@nota_bp.route("/export/customer")
@permission_required("nota.view")
def export_customers():
    year, month = _report_period_filter()
    rows = [[row.name, row.team_name, row.brand, row.invoice_count, row.total] for row in top_customers(_brand_filter() or None, year, month)]
    workbook = workbook_response("Customer", ["Nama Customer", "Tim", "Brand", "Jumlah Nota", "Total Omset"], rows)
    return _excel_file(workbook, "customer.xlsx")


@nota_bp.route("/baru", methods=["GET", "POST"])
@permission_required("nota.manage")
def create():
    if request.method == "POST":
        so_id = request.form.get("so_id")
        existing_nota = get_nota_by_so_id(so_id)
        if existing_nota:
            flash("Sales Order ini sudah memiliki Nota. Anda diarahkan ke Nota yang sudah ada.", "warning")
            return redirect(url_for("nota.detail", nota_id=existing_nota.id))
        source_so = get_sales_order(int(so_id)) if str(so_id or "").isdigit() else None
        errors = validate_nota_form(request.form)
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "nota/form.html",
                **_form_context(nota=None, form=request.form, item_rows=posted_item_rows(request.form), source_so=source_so),
            )
        nota = create_nota(request.form, current_user)
        flash("Nota berhasil dibuat.", "success")
        return redirect(url_for("nota.detail", nota_id=nota.id))

    so_id = request.args.get("so_id")
    if str(so_id or "").isdigit():
        existing_nota = get_nota_by_so_id(so_id)
        if existing_nota:
            flash("Sales Order ini sudah memiliki Nota. Anda diarahkan ke Nota yang sudah ada.", "warning")
            return redirect(url_for("nota.detail", nota_id=existing_nota.id))
        source_so = get_sales_order(int(so_id))
        return render_template(
            "nota/form.html",
            **_form_context(
                nota=None,
                form=form_data_from_sales_order(source_so),
                item_rows=item_rows_from_sales_order(source_so),
                source_so=source_so,
            ),
        )
    return render_template("nota/form.html", **_form_context(nota=None, form={}, item_rows=[], source_so=None))


@nota_bp.route("/<int:nota_id>")
@permission_required("nota.view")
def detail(nota_id):
    nota = get_nota(nota_id)
    return render_template(
        "nota/detail.html",
        nota=nota,
        items=sorted(nota.items, key=lambda item: item.sort_order),
        payments=sorted(nota.payments, key=lambda payment: (payment.payment_date, payment.id)),
        totals=totals(nota),
        invoice_status=calculate_invoice_status(nota),
    )


@nota_bp.route("/<int:nota_id>/edit", methods=["GET", "POST"])
@permission_required("nota.manage")
def edit(nota_id):
    nota = get_nota(nota_id)
    if request.method == "POST":
        errors = validate_nota_form(request.form)
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("nota/form.html", **_form_context(nota=nota, form=request.form, item_rows=posted_item_rows(request.form)))
        update_nota(nota, request.form)
        flash("Nota berhasil diperbarui.", "success")
        return redirect(url_for("nota.detail", nota_id=nota.id))
    return render_template("nota/form.html", **_form_context(nota=nota, form={}, item_rows=item_rows_for_form(nota)))


@nota_bp.route("/<int:nota_id>/pembayaran", methods=["POST"])
@permission_required("nota.manage")
def payment(nota_id):
    nota = get_nota(nota_id)
    try:
        add_payment(nota, request.form, current_user)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Pembayaran berhasil ditambahkan.", "success")
    return redirect(url_for("nota.detail", nota_id=nota.id))


@nota_bp.route("/<int:nota_id>/pembayaran/<int:payment_id>/edit", methods=["POST"])
@permission_required("nota.manage")
def payment_edit(nota_id, payment_id):
    nota = get_nota(nota_id)
    payment = get_payment(payment_id)
    if payment.nota_id != nota.id:
        abort(404)
    try:
        update_payment(payment, request.form, current_user)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Pembayaran berhasil diperbarui.", "success")
    return redirect(url_for("nota.detail", nota_id=nota.id))


@nota_bp.route("/<int:nota_id>/pembayaran/<int:payment_id>/void", methods=["POST"])
@permission_required("nota.manage")
def payment_void(nota_id, payment_id):
    nota = get_nota(nota_id)
    payment = get_payment(payment_id)
    if payment.nota_id != nota.id:
        abort(404)
    try:
        void_payment(payment, request.form.get("void_reason"), current_user)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Pembayaran berhasil dibatalkan.", "success")
    return redirect(url_for("nota.detail", nota_id=nota.id))


@nota_bp.route("/<int:nota_id>/print")
@permission_required("nota.view")
def print_view(nota_id):
    nota = get_nota(nota_id)
    return render_template(
        "nota/print.html",
        title="Nota",
        nota=nota,
        invoice_brand=get_invoice_brand(nota.brand.name if nota.brand else None),
        items=sorted(nota.items, key=lambda item: item.sort_order),
        payments=sorted(nota.payments, key=lambda payment: (payment.payment_date, payment.id)),
        totals=totals(nota),
        invoice_status=calculate_invoice_status(nota),
    )


@nota_bp.route("/<int:nota_id>/pdf/internal")
@permission_required("nota.view")
def internal_pdf(nota_id):
    nota = get_nota(nota_id)
    pdf = build_internal_note_pdf(
        _pdf_invoice(nota),
        _pdf_items(nota),
        _pdf_payments(nota),
        totals(nota),
    )
    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=nota_pdf_download_name(nota),
    )


@nota_bp.route("/<int:nota_id>/pdf/customer")
@permission_required("nota.view")
def customer_pdf(nota_id):
    nota = get_nota(nota_id)
    invoice = _pdf_invoice(nota, mapped_brand=True)
    if invoice["brand"] == "FF Apparel":
        pdf = build_ff_apparel_pdf(invoice, _pdf_items(nota), _pdf_payments(nota), totals(nota))
    else:
        pdf = build_customer_invoice_pdf(invoice, _pdf_items(nota), totals(nota))
    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=nota_pdf_download_name(nota),
    )


def _excel_file(workbook, filename):
    return send_file(
        workbook,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


def _pdf_invoice(nota, mapped_brand=False):
    brand_name = nota.brand.name if nota.brand else "Evpro"
    if mapped_brand:
        invoice_brand = get_invoice_brand(brand_name)
        brand_name = invoice_brand["display_name"] if invoice_brand["display_name"] in ("RDR Apparel", "FF Apparel") else "Evpro"
    return {
        "id": nota.id,
        "invoice_number": display_nota_number(nota),
        "brand": brand_name,
        "order_date": nota.order_date,
        "customer_name": nota.customer.name,
        "team_name": nota.team_name,
        "phone": nota.customer.phone,
        "address": nota.customer.address,
        "status": calculate_invoice_status(nota),
        "notes": nota.notes,
    }


def _pdf_items(nota):
    return [
        {
            "product_code": item.product_code,
            "description": item.description,
            "quantity": item.quantity,
            "price": item.price,
            "subtotal": item.subtotal,
        }
        for item in sorted(nota.items, key=lambda item: item.sort_order)
    ]


def _pdf_payments(nota):
    return [
        {
            "payment_date": payment.payment_date,
            "amount": payment.amount,
            "description": payment.description,
        }
        for payment in sorted(nota.payments, key=lambda payment: (payment.payment_date, payment.id))
    ]
