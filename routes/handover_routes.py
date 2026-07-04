from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from services.handover_service import (
    default_pickup_date,
    get_handover_order,
    handover_filter_from_args,
    handover_summary,
    month_label,
    mark_picked_up,
    pending_pickup_rows,
    picked_up_monthly_summary,
    picked_up_rows,
    year_options,
)
from services.handover_pdf_service import build_pending_handover_pdf, build_picked_handover_pdf
from services.pdf_render_service import render_first_pdf_page_to_jpg
from utils.permissions import permission_required


handover_bp = Blueprint("handover", __name__, url_prefix="/serah-terima")


@handover_bp.route("/", endpoint="index")
@permission_required("handover.view")
def index():
    active_tab = request.args.get("tab", "belum")
    selected_month, selected_year = handover_filter_from_args(request.args)
    return render_template(
        "handover/index.html",
        active_tab=active_tab if active_tab in {"belum", "sudah"} else "belum",
        pending_rows=pending_pickup_rows(),
        picked_rows=picked_up_rows(selected_month, selected_year),
        picked_summary=picked_up_monthly_summary(selected_month, selected_year),
        summary=handover_summary(),
        selected_month=selected_month,
        selected_year=selected_year,
        month_options=range(1, 13),
        month_label=month_label,
        year_options=year_options(selected_year),
    )


@handover_bp.route("/belum-diambil/pdf", endpoint="pending_pdf")
@permission_required("handover.view")
def pending_pdf():
    pdf_buffer = build_pending_handover_pdf(pending_pickup_rows())
    response = send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=False,
        download_name="serah-terima-belum-diambil.pdf",
    )
    response.headers["Content-Disposition"] = 'inline; filename="serah-terima-belum-diambil.pdf"'
    return response


@handover_bp.route("/belum-diambil/jpg", endpoint="pending_jpg")
@permission_required("handover.view")
def pending_jpg():
    pdf_buffer = build_pending_handover_pdf(pending_pickup_rows())
    jpg_buffer = render_first_pdf_page_to_jpg(pdf_buffer)
    filename = f"serah_terima_belum_diambil_{date.today().strftime('%Y-%m')}.jpg"
    return send_file(
        jpg_buffer,
        mimetype="image/jpeg",
        as_attachment=True,
        download_name=filename,
    )


@handover_bp.route("/sudah-diambil/pdf", endpoint="picked_pdf")
@permission_required("handover.view")
def picked_pdf():
    selected_month, selected_year = handover_filter_from_args(request.args)
    pdf_buffer = build_picked_handover_pdf(
        picked_up_rows(selected_month, selected_year),
        selected_month,
        selected_year,
    )
    month_part = f"{selected_month:02d}" if selected_month else "semua-bulan"
    year_part = str(selected_year) if selected_year else "semua-tahun"
    filename = f"serah-terima-sudah-diambil-{year_part}-{month_part}.pdf"
    response = send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=filename,
    )
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


@handover_bp.route("/<int:sales_order_id>/diambil", methods=["GET", "POST"], endpoint="pickup")
@permission_required("handover.manage")
def pickup(sales_order_id):
    order = get_handover_order(sales_order_id)
    if request.method == "POST":
        try:
            mark_picked_up(order, request.form, current_user)
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template(
                "handover/pickup.html",
                order=order,
                form=request.form,
                default_date=default_pickup_date(),
            )
        flash(f"Serah terima {order.so_number} berhasil ditandai sudah diambil.", "success")
        return redirect(url_for("handover.index", tab="sudah"))
    return render_template(
        "handover/pickup.html",
        order=order,
        form={},
        default_date=default_pickup_date(),
    )
