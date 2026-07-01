from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for

from flask_login import current_user, login_required

from services.nota_service import (
    NOTA_STATUSES,
    add_payment,
    create_nota,
    dashboard_stats,
    delete_nota,
    delete_product,
    format_so_number_for_invoice,
    form_data_from_sales_order,
    get_nota,
    get_invoice_brand,
    get_nota_by_so_id,
    income_payments,
    income_summary,
    invoice_export_rows,
    item_rows_from_sales_order,
    item_rows_for_form,
    invoice_brand_filter_options,
    list_invoice_brand_options,
    list_brands,
    list_customers_as_dicts,
    list_notas,
    list_products,
    list_products_as_dicts,
    monthly_revenue,
    nota_rows,
    posted_item_rows,
    receivables,
    report_nota_rows,
    top_customers,
    totals,
    update_nota,
    update_status,
    upsert_product,
    validate_nota_form,
    workbook_response,
    yearly_revenue,
)
from services.nota_pdf_ff_apparel_service import build_ff_apparel_pdf
from services.nota_pdf_service import build_customer_invoice_pdf, build_internal_note_pdf
from services.sales_order_service import get_sales_order


nota_bp = Blueprint("nota", __name__, url_prefix="/nota")


def _admin_required():
    if not current_user.is_admin:
        abort(403)


def _form_context(**kwargs):
    context = {
        "statuses": NOTA_STATUSES,
        "brands": list_brands(),
        "products": list_products_as_dicts(),
        "customers": list_customers_as_dicts(),
        "today": date.today().isoformat(),
    }
    context.update(kwargs)
    return context


def _brand_filter():
    return request.args.get("brand", "").strip()


@nota_bp.route("/dashboard")
@login_required
def dashboard():
    _admin_required()
    brand = _brand_filter()
    return render_template(
        "nota/dashboard.html",
        stats=dashboard_stats(brand or None),
        monthly=monthly_revenue(brand or None),
        yearly=yearly_revenue(brand or None),
        brands=list_invoice_brand_options(),
        active_brand=brand,
    )


@nota_bp.route("/")
@login_required
def index():
    _admin_required()
    search = {
        "q": request.args.get("q", "").strip(),
        "status": request.args.get("status", "").strip(),
        "brand_group": request.args.get("brand_group", "").strip(),
    }
    return render_template(
        "nota/index.html",
        notas=list_notas(search),
        statuses=NOTA_STATUSES,
        brand_groups=invoice_brand_filter_options(),
        format_so_number_for_invoice=format_so_number_for_invoice,
        search=search["q"],
        active_status=search["status"],
        active_brand_group=search["brand_group"],
    )


@nota_bp.route("/produk", methods=["GET", "POST"])
@login_required
def products():
    _admin_required()
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
@login_required
def delete_product_view(product_id):
    _admin_required()
    delete_product(product_id)
    flash("Produk berhasil dihapus.", "success")
    return redirect(url_for("nota.products"))


@nota_bp.route("/<int:nota_id>/delete", methods=["POST"])
@login_required
def delete(nota_id):
    _admin_required()
    nota = get_nota(nota_id)
    delete_nota(nota)
    flash("Nota berhasil dihapus.", "success")
    return redirect(url_for("nota.index"))


@nota_bp.route("/laporan")
@login_required
def reports():
    _admin_required()
    brand = _brand_filter()
    return render_template(
        "nota/reports/index.html",
        stats=dashboard_stats(brand or None),
        monthly=monthly_revenue(brand or None),
        yearly=yearly_revenue(brand or None),
        customers=top_customers(brand or None),
        brands=list_invoice_brand_options(),
        active_brand=brand,
    )


@nota_bp.route("/laporan/customer")
@login_required
def customer_report():
    _admin_required()
    brand = _brand_filter()
    return render_template(
        "nota/reports/customers.html",
        customers=top_customers(brand or None),
        brands=list_invoice_brand_options(),
        active_brand=brand,
    )


@nota_bp.route("/piutang")
@login_required
def receivables_page():
    _admin_required()
    brand = _brand_filter()
    status = request.args.get("status", "").strip()
    return render_template(
        "nota/reports/receivables.html",
        invoices=receivables(brand or None, status or None),
        statuses=NOTA_STATUSES,
        brands=list_invoice_brand_options(),
        active_brand=brand,
        active_status=status,
    )


@nota_bp.route("/pemasukan")
@login_required
def income_page():
    _admin_required()
    brand = _brand_filter()
    return render_template(
        "nota/reports/income.html",
        payments=income_payments(brand or None),
        summary=income_summary(brand or None),
        brands=list_invoice_brand_options(),
        active_brand=brand,
    )


@nota_bp.route("/export/nota")
@login_required
def export_invoices():
    _admin_required()
    rows = invoice_export_rows(report_nota_rows(_brand_filter() or None))
    workbook = workbook_response(
        "Semua Nota",
        ["Nomor Nota", "Tanggal", "Brand", "Customer", "Tim", "Total Nota", "Sudah Dibayar", "Sisa Piutang", "Status"],
        rows,
    )
    return _excel_file(workbook, "semua-nota.xlsx")


@nota_bp.route("/export/piutang")
@login_required
def export_receivables():
    _admin_required()
    rows = invoice_export_rows(receivables(_brand_filter() or None))
    workbook = workbook_response(
        "Piutang",
        ["Nomor Nota", "Tanggal", "Brand", "Customer", "Tim", "Total Nota", "Sudah Dibayar", "Sisa Piutang", "Status"],
        rows,
    )
    return _excel_file(workbook, "piutang.xlsx")


@nota_bp.route("/export/omset-bulanan")
@login_required
def export_monthly_revenue():
    _admin_required()
    rows = [[row.month, row.total] for row in monthly_revenue(_brand_filter() or None)]
    workbook = workbook_response("Omset Bulanan", ["Bulan", "Omset"], rows)
    return _excel_file(workbook, "omset-bulanan.xlsx")


@nota_bp.route("/export/customer")
@login_required
def export_customers():
    _admin_required()
    rows = [[row.name, row.team_name, row.brand, row.invoice_count, row.total] for row in top_customers(_brand_filter() or None)]
    workbook = workbook_response("Customer", ["Nama Customer", "Tim", "Brand", "Jumlah Nota", "Total Omset"], rows)
    return _excel_file(workbook, "customer.xlsx")


@nota_bp.route("/baru", methods=["GET", "POST"])
@login_required
def create():
    _admin_required()
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
@login_required
def detail(nota_id):
    _admin_required()
    nota = get_nota(nota_id)
    return render_template(
        "nota/detail.html",
        nota=nota,
        items=sorted(nota.items, key=lambda item: item.sort_order),
        payments=sorted(nota.payments, key=lambda payment: (payment.payment_date, payment.id)),
        totals=totals(nota),
        statuses=NOTA_STATUSES,
    )


@nota_bp.route("/<int:nota_id>/edit", methods=["GET", "POST"])
@login_required
def edit(nota_id):
    _admin_required()
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
@login_required
def payment(nota_id):
    _admin_required()
    nota = get_nota(nota_id)
    try:
        add_payment(nota, request.form)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Pembayaran berhasil ditambahkan.", "success")
    return redirect(url_for("nota.detail", nota_id=nota.id))


@nota_bp.route("/<int:nota_id>/status", methods=["POST"])
@login_required
def status(nota_id):
    _admin_required()
    nota = get_nota(nota_id)
    try:
        update_status(nota, request.form.get("status"))
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Status order berhasil diubah.", "success")
    return redirect(url_for("nota.detail", nota_id=nota.id))


@nota_bp.route("/<int:nota_id>/print")
@login_required
def print_view(nota_id):
    _admin_required()
    nota = get_nota(nota_id)
    return render_template(
        "nota/print.html",
        title="Nota",
        nota=nota,
        invoice_brand=get_invoice_brand(nota.brand.name if nota.brand else None),
        items=sorted(nota.items, key=lambda item: item.sort_order),
        payments=sorted(nota.payments, key=lambda payment: (payment.payment_date, payment.id)),
        totals=totals(nota),
    )


@nota_bp.route("/<int:nota_id>/pdf/internal")
@login_required
def internal_pdf(nota_id):
    _admin_required()
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
        download_name=f"nota-internal-{nota.nota_number}.pdf",
    )


@nota_bp.route("/<int:nota_id>/pdf/customer")
@login_required
def customer_pdf(nota_id):
    _admin_required()
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
        download_name=f"invoice-customer-{nota.id}.pdf",
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
        "invoice_number": nota.nota_number,
        "brand": brand_name,
        "order_date": nota.order_date,
        "customer_name": nota.customer.name,
        "team_name": nota.team_name,
        "phone": nota.customer.phone,
        "address": nota.customer.address,
        "status": nota.status,
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
