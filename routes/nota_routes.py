from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from flask_login import current_user, login_required

from services.nota_service import (
    NOTA_STATUSES,
    add_payment,
    create_nota,
    form_data_from_sales_order,
    get_nota,
    get_nota_by_so_id,
    item_rows_from_sales_order,
    item_rows_for_form,
    list_brands,
    list_customers_as_dicts,
    list_notas,
    list_products_as_dicts,
    posted_item_rows,
    totals,
    update_nota,
    update_status,
    validate_nota_form,
)
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


@nota_bp.route("/")
@login_required
def index():
    _admin_required()
    search = {
        "q": request.args.get("q", "").strip(),
        "status": request.args.get("status", "").strip(),
        "brand_id": request.args.get("brand_id", "").strip(),
    }
    return render_template(
        "nota/index.html",
        notas=list_notas(search),
        statuses=NOTA_STATUSES,
        brands=list_brands(),
        search=search["q"],
        active_status=search["status"],
        active_brand_id=search["brand_id"],
    )


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
        items=sorted(nota.items, key=lambda item: item.sort_order),
        payments=sorted(nota.payments, key=lambda payment: (payment.payment_date, payment.id)),
        totals=totals(nota),
    )
