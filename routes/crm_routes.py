from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models.crm import CUSTOMER_SOURCES, CUSTOMER_STATUSES, FOLLOW_UP_STATUSES, LEAD_SOURCES, LEAD_STATUSES
from services.crm_service import (
    WA_TEMPLATE_CATEGORIES,
    create_whatsapp_template,
    create_lead,
    create_follow_up,
    crm_summary,
    customer_options,
    delete_whatsapp_template,
    get_customer,
    get_lead,
    get_whatsapp_template,
    lead_options,
    lead_whatsapp_template_options,
    list_whatsapp_templates,
    list_customers,
    list_follow_ups,
    list_leads,
    next_whatsapp_template_order,
    send_lead_whatsapp,
    send_customer_whatsapp,
    toggle_whatsapp_template,
    update_lead,
    update_customer,
    update_whatsapp_template,
    users_for_assignment,
)


crm_bp = Blueprint("crm", __name__, url_prefix="/crm")


def _crm_allowed():
    return current_user.is_authenticated and current_user.is_admin


def _access_denied():
    return render_template("crm/access_denied.html"), 403


@crm_bp.before_request
@login_required
def require_admin():
    if not _crm_allowed():
        return _access_denied()
    return None


@crm_bp.route("/")
def dashboard():
    return render_template("crm/dashboard.html", summary=crm_summary())


@crm_bp.route("/customers")
def customers():
    search = {
        "q": request.args.get("q", "").strip(),
        "source": request.args.get("source", "").strip(),
        "status": request.args.get("status", "").strip(),
    }
    return render_template(
        "crm/customers.html",
        customers=list_customers(search),
        wa_templates=lead_whatsapp_template_options(),
        sources=CUSTOMER_SOURCES,
        statuses=CUSTOMER_STATUSES,
        search=search,
        today=date.today().isoformat(),
    )


@crm_bp.route("/leads")
def leads():
    search = {
        "status": request.args.get("status", "").strip(),
        "source": request.args.get("source", "").strip(),
        "next_follow_up_date": request.args.get("next_follow_up_date", "").strip(),
        "assigned": request.args.get("assigned", "").strip(),
    }
    return render_template(
        "crm/leads.html",
        leads=list_leads(search),
        statuses=LEAD_STATUSES,
        sources=LEAD_SOURCES,
        wa_templates=lead_whatsapp_template_options(),
        search=search,
        today=date.today().isoformat(),
    )


@crm_bp.route("/leads/new", methods=["GET", "POST"])
def lead_new():
    if request.method == "POST":
        try:
            lead = create_lead(request.form, current_user)
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Lead berhasil ditambahkan.", "success")
            return redirect(url_for("crm.lead_detail", lead_id=lead.id))
    return render_template(
        "crm/lead_form.html",
        lead=None,
        form=request.form if request.method == "POST" else {},
        statuses=LEAD_STATUSES,
        sources=LEAD_SOURCES,
        users=users_for_assignment(),
        today=date.today().isoformat(),
    )


@crm_bp.route("/leads/<int:lead_id>")
def lead_detail(lead_id):
    lead = get_lead(lead_id)
    return render_template(
        "crm/lead_detail.html",
        lead=lead,
        follow_up_statuses=FOLLOW_UP_STATUSES,
        wa_templates=lead_whatsapp_template_options(),
        today=date.today().isoformat(),
    )


@crm_bp.route("/leads/<int:lead_id>/send-wa", methods=["POST"])
def lead_send_whatsapp(lead_id):
    lead = get_lead(lead_id)
    try:
        wa_url = send_lead_whatsapp(lead, request.form.get("template_id"), request.form.get("message"), current_user)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(request.referrer or url_for("crm.lead_detail", lead_id=lead.id))
    return redirect(wa_url)


@crm_bp.route("/leads/<int:lead_id>/follow-ups", methods=["POST"])
def add_lead_follow_up(lead_id):
    lead = get_lead(lead_id)
    form = request.form.copy()
    form["follow_up_type"] = "Lead"
    form["lead_id"] = str(lead.id)
    try:
        create_follow_up(form, current_user)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Follow up lead berhasil ditambahkan.", "success")
    return redirect(url_for("crm.lead_detail", lead_id=lead.id))


@crm_bp.route("/leads/<int:lead_id>/edit", methods=["GET", "POST"])
def lead_edit(lead_id):
    lead = get_lead(lead_id)
    if request.method == "POST":
        try:
            update_lead(lead, request.form, current_user)
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Lead berhasil diperbarui.", "success")
            return redirect(url_for("crm.lead_detail", lead_id=lead.id))
    return render_template(
        "crm/lead_form.html",
        lead=lead,
        form=request.form if request.method == "POST" else {},
        statuses=LEAD_STATUSES,
        sources=LEAD_SOURCES,
        users=users_for_assignment(),
        today=date.today().isoformat(),
    )


@crm_bp.route("/leads/<int:lead_id>/create-so")
def lead_create_so(lead_id):
    lead = get_lead(lead_id)
    if lead.status != "Closing":
        flash("Ubah status lead menjadi Closing sebelum membuat Surat Order.", "warning")
        return redirect(url_for("crm.lead_detail", lead_id=lead.id))
    if lead.converted_so_id:
        flash("Lead ini sudah dikonversi ke Surat Order.", "warning")
        return redirect(url_for("sales_orders.detail", sales_order_id=lead.converted_so_id))
    return redirect(url_for("sales_orders.create", lead_id=lead.id))


@crm_bp.route("/customers/<int:customer_id>")
def customer_detail(customer_id):
    customer = get_customer(customer_id)
    return render_template(
        "crm/customer_detail.html",
        customer=customer,
        follow_up_statuses=FOLLOW_UP_STATUSES,
        wa_templates=lead_whatsapp_template_options(),
        today=date.today().isoformat(),
    )


@crm_bp.route("/customers/<int:customer_id>/send-wa", methods=["POST"])
def customer_send_whatsapp(customer_id):
    customer = get_customer(customer_id)
    try:
        wa_url = send_customer_whatsapp(customer, request.form.get("template_id"), request.form.get("message"), current_user)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(request.referrer or url_for("crm.customer_detail", customer_id=customer.id))
    return redirect(wa_url)


@crm_bp.route("/customers/<int:customer_id>/edit", methods=["GET", "POST"])
def customer_edit(customer_id):
    customer = get_customer(customer_id)
    if request.method == "POST":
        update_customer(customer, request.form)
        flash("Data customer berhasil diperbarui.", "success")
        return redirect(url_for("crm.customer_detail", customer_id=customer.id))
    return render_template(
        "crm/customer_edit.html",
        customer=customer,
        sources=CUSTOMER_SOURCES,
        statuses=CUSTOMER_STATUSES,
    )


@crm_bp.route("/customers/<int:customer_id>/follow-ups", methods=["POST"])
def add_customer_follow_up(customer_id):
    customer = get_customer(customer_id)
    form = request.form.copy()
    form["follow_up_type"] = "Customer"
    form["customer_id"] = str(customer.id)
    try:
        create_follow_up(form, current_user)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Follow up berhasil ditambahkan.", "success")
    return redirect(url_for("crm.customer_detail", customer_id=customer.id))


@crm_bp.route("/follow-ups")
def follow_ups():
    search = {
        "follow_up_type": request.args.get("follow_up_type", "").strip(),
        "status": request.args.get("status", "").strip(),
        "next_follow_up_date": request.args.get("next_follow_up_date", "").strip(),
        "name": request.args.get("name", "").strip(),
        "admin": request.args.get("admin", "").strip(),
        "source": request.args.get("source", "").strip(),
    }
    sources = list(dict.fromkeys([*CUSTOMER_SOURCES, *LEAD_SOURCES]))
    return render_template(
        "crm/follow_ups.html",
        follow_ups=list_follow_ups(search),
        leads=lead_options(),
        customers=customer_options(),
        sources=sources,
        statuses=FOLLOW_UP_STATUSES,
        search=search,
        today=date.today().isoformat(),
    )


@crm_bp.route("/follow-ups", methods=["POST"])
def create_follow_up_route():
    try:
        follow_up = create_follow_up(request.form, current_user)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Follow up berhasil ditambahkan.", "success")
        if follow_up.follow_up_type == "Lead" and follow_up.lead_id:
            return redirect(url_for("crm.lead_detail", lead_id=follow_up.lead_id))
        return redirect(url_for("crm.customer_detail", customer_id=follow_up.customer_id))
    return redirect(url_for("crm.follow_ups"))


@crm_bp.route("/wa-templates")
def wa_templates():
    search = {
        "q": request.args.get("q", "").strip(),
        "category": request.args.get("category", "").strip(),
        "status": request.args.get("status", "").strip(),
    }
    return render_template(
        "crm/wa_templates.html",
        templates=list_whatsapp_templates(search),
        categories=WA_TEMPLATE_CATEGORIES,
        search=search,
    )


@crm_bp.route("/wa-templates/new", methods=["GET", "POST"])
def wa_template_new():
    if request.method == "POST":
        try:
            create_whatsapp_template(request.form)
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Template WA berhasil ditambahkan.", "success")
            return redirect(url_for("crm.wa_templates"))
    return render_template(
        "crm/wa_template_form.html",
        template=None,
        form=request.form if request.method == "POST" else {},
        categories=WA_TEMPLATE_CATEGORIES,
        default_sort_order=next_whatsapp_template_order(),
    )


@crm_bp.route("/wa-templates/<int:template_id>/edit", methods=["GET", "POST"])
def wa_template_edit(template_id):
    template = get_whatsapp_template(template_id)
    if request.method == "POST":
        try:
            update_whatsapp_template(template, request.form)
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Template WA berhasil diperbarui.", "success")
            return redirect(url_for("crm.wa_templates"))
    return render_template(
        "crm/wa_template_form.html",
        template=template,
        form=request.form if request.method == "POST" else {},
        categories=WA_TEMPLATE_CATEGORIES,
        default_sort_order=template.sort_order,
    )


@crm_bp.route("/wa-templates/<int:template_id>/toggle", methods=["POST"])
def wa_template_toggle(template_id):
    template = get_whatsapp_template(template_id)
    toggle_whatsapp_template(template)
    flash("Status template WA berhasil diperbarui.", "success")
    return redirect(url_for("crm.wa_templates"))


@crm_bp.route("/wa-templates/<int:template_id>/delete", methods=["POST"])
def wa_template_delete(template_id):
    template = get_whatsapp_template(template_id)
    delete_whatsapp_template(template)
    flash("Template WA berhasil dihapus.", "success")
    return redirect(url_for("crm.wa_templates"))
