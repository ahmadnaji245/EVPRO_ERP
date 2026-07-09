from datetime import date, datetime
from urllib.parse import quote

from sqlalchemy import func, or_

from database.db import db
from models import Brand, Customer, FollowUp, Lead, Nota, SalesOrder, User, WhatsAppTemplate
from models.crm import CUSTOMER_SOURCES, FOLLOW_UP_STATUSES, LEAD_SOURCES, LEAD_STATUSES


WA_TEMPLATE_CATEGORIES = ("Awal", "Harga", "Desain", "DP", "Follow Up", "Repeat", "After Sales", "Reminder", "Lainnya")


DEFAULT_WA_TEMPLATES = (
    (
        "baru",
        "Customer baru / lead baru",
        "Awal",
        "Halo kak {name}, terima kasih sudah menghubungi EVPRO/RDR.\n\n"
        "Saya bantu cek kebutuhannya dulu ya kak. Untuk pesanannya rencana dipakai untuk olahraga apa, butuh berapa pcs, "
        "atasan saja atau set atasan-bawahan, ada deadline pemakaian, dan desainnya sudah ada atau masih perlu dibantu buatkan?",
    ),
    (
        "harga",
        "Cek harga dulu",
        "Harga",
        "Siap kak, untuk kisaran harga bisa menyesuaikan paket dan spesifikasi.\n\n"
        "- Seri Premium: Rp185.000/set jika ada tambahan kerah\n"
        "- Seri Hemat: Rp165.000/set jika ada tambahan kerah\n\n"
        "Biar saya bantu arahkan yang paling sesuai, rencana jumlah pesanannya berapa pcs, deadline kapan, modelnya seperti apa, "
        "dan desainnya sudah ada atau masih perlu dibantu?",
    ),
    (
        "desain_siap",
        "Sudah punya desain",
        "Desain",
        "Siap kak, kalau desain dari kakak sudah siap, nanti bisa langsung kami bantu cek untuk produksi. "
        "Kalau sewaktu-waktu butuh revisi kecil atau penyesuaian desain, bisa kami bantu juga sesuai kebutuhan.",
    ),
    (
        "belum_respon_3_hari",
        "Belum respon 3 hari",
        "Follow Up",
        "Tidak apa-apa kak, saya bantu follow up kembali. Barangkali masih dipertimbangkan untuk kebutuhan jerseynya.",
    ),
    (
        "belum_respon_7_hari",
        "Belum respon 7 hari",
        "Follow Up",
        "Saya izin follow up kembali ya kak. Kalau memang belum jadi order tidak apa-apa, tapi kalau masih butuh pertimbangan bahan, "
        "harga, atau desain, nanti bisa saya bantu jelaskan.",
    ),
    (
        "dp",
        "Menunggu DP",
        "DP",
        "Siap kak, untuk lanjut produksi nanti bisa dibantu DP terlebih dahulu supaya jadwal produksi bisa kami amankan.",
    ),
    (
        "repeat_order",
        "Repeat order",
        "Repeat",
        "Terima kasih kak sebelumnya sudah pernah order. Kalau ada kebutuhan jersey tambahan atau desain baru, nanti bisa kami bantu kembali.",
    ),
)


def normalize_phone(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if digits.startswith("62"):
        return digits
    if digits.startswith("0"):
        return "62" + digits[1:]
    return digits


def list_customers(search=None):
    search = search or {}
    query = Customer.query
    q = str(search.get("q") or "").strip()
    source = str(search.get("source") or "").strip()
    status = str(search.get("status") or "").strip()
    if q:
        needle = f"%{q}%"
        query = query.filter(or_(Customer.name.ilike(needle), Customer.whatsapp.ilike(needle), Customer.address.ilike(needle)))
    if source:
        query = query.filter(Customer.source == source)
    if status:
        query = query.filter(Customer.status == status)
    return query.order_by(Customer.updated_at.desc(), Customer.id.desc()).all()


def get_customer(customer_id):
    return Customer.query.get_or_404(customer_id)


def customer_options():
    return Customer.query.order_by(Customer.name.asc()).all()


def lead_options():
    return Lead.query.order_by(Lead.name.asc()).all()


def list_follow_ups(search=None):
    search = search or {}
    query = (
        FollowUp.query.outerjoin(Customer, FollowUp.customer_id == Customer.id)
        .outerjoin(Lead, FollowUp.lead_id == Lead.id)
        .outerjoin(User, FollowUp.admin_id == User.id)
    )
    follow_up_type = str(search.get("follow_up_type") or "").strip()
    status = str(search.get("status") or "").strip()
    name = str(search.get("name") or search.get("customer") or "").strip()
    admin = str(search.get("admin") or "").strip()
    source = str(search.get("source") or "").strip()
    next_date = _parse_date(search.get("next_follow_up_date"))
    if follow_up_type in ("Lead", "Customer"):
        query = query.filter(FollowUp.follow_up_type == follow_up_type)
    if status:
        query = query.filter(FollowUp.status == status)
    if name:
        query = query.filter(or_(Customer.name.ilike(f"%{name}%"), Lead.name.ilike(f"%{name}%")))
    if admin:
        query = query.filter(or_(User.name.ilike(f"%{admin}%"), FollowUp.admin_name.ilike(f"%{admin}%")))
    if source:
        query = query.filter(or_(Customer.source == source, Lead.source == source))
    if next_date:
        query = query.filter(FollowUp.next_follow_up_date == next_date)
    rows = query.all()
    today = date.today()
    return sorted(
        rows,
        key=lambda item: (
            0 if item.next_follow_up_date and item.next_follow_up_date <= today and item.status not in ("Closing", "Tidak jadi") else 1,
            item.next_follow_up_date or date.max,
            item.follow_up_date,
            item.id,
        ),
    )


def list_leads(search=None):
    search = search or {}
    query = Lead.query.outerjoin(User, Lead.assigned_to == User.id)
    status = str(search.get("status") or "").strip()
    source = str(search.get("source") or "").strip()
    assigned = str(search.get("assigned") or "").strip()
    follow_up_date = _parse_date(search.get("next_follow_up_date"))
    if status:
        query = query.filter(Lead.status == status)
    if source:
        query = query.filter(Lead.source == source)
    if follow_up_date:
        query = query.filter(Lead.next_follow_up_date == follow_up_date)
    if assigned:
        query = query.filter(or_(User.name.ilike(f"%{assigned}%"), User.username.ilike(f"%{assigned}%")))
    rows = query.all()
    today = date.today()
    return sorted(
        rows,
        key=lambda lead: (
            0 if lead.next_follow_up_date and lead.next_follow_up_date <= today and lead.status not in ("Closing", "Tidak jadi") else 1,
            lead.next_follow_up_date or date.max,
            lead.updated_at or lead.created_at,
            lead.id,
        ),
    )


def get_lead(lead_id):
    return Lead.query.get_or_404(lead_id)


def create_lead(form, user=None):
    lead = Lead()
    _fill_lead(lead, form, user)
    db.session.add(lead)
    db.session.commit()
    return lead


def update_lead(lead, form, user=None):
    _fill_lead(lead, form, user)
    db.session.commit()
    return lead


def lead_whatsapp_template_options():
    return whatsapp_template_options()


def whatsapp_template_options():
    return (
        WhatsAppTemplate.query.filter_by(is_active=True, is_deleted=False)
        .order_by(WhatsAppTemplate.sort_order.asc(), WhatsAppTemplate.category.asc(), WhatsAppTemplate.name.asc())
        .all()
    )


def list_whatsapp_templates(search=None):
    search = search or {}
    query = WhatsAppTemplate.query.filter_by(is_deleted=False)
    q = str(search.get("q") or "").strip()
    category = str(search.get("category") or "").strip()
    status = str(search.get("status") or "").strip()
    if q:
        query = query.filter(WhatsAppTemplate.name.ilike(f"%{q}%"))
    if category:
        query = query.filter(WhatsAppTemplate.category == category)
    if status == "active":
        query = query.filter(WhatsAppTemplate.is_active.is_(True))
    elif status == "inactive":
        query = query.filter(WhatsAppTemplate.is_active.is_(False))
    return query.order_by(WhatsAppTemplate.sort_order.asc(), WhatsAppTemplate.category.asc(), WhatsAppTemplate.name.asc()).all()


def get_whatsapp_template(template_id):
    return WhatsAppTemplate.query.filter_by(id=template_id, is_deleted=False).first_or_404()


def create_whatsapp_template(form):
    template = WhatsAppTemplate()
    _fill_whatsapp_template(template, form)
    template.key = _generate_whatsapp_template_key(template.name)
    db.session.add(template)
    db.session.commit()
    return template


def update_whatsapp_template(template, form):
    _fill_whatsapp_template(template, form)
    db.session.commit()
    return template


def toggle_whatsapp_template(template):
    template.is_active = not template.is_active
    template.updated_at = datetime.utcnow()
    db.session.commit()
    return template


def delete_whatsapp_template(template):
    template.is_deleted = True
    template.is_active = False
    template.updated_at = datetime.utcnow()
    db.session.commit()
    return template


def _fill_whatsapp_template(template, form):
    name = str(form.get("name") or "").strip()
    category = str(form.get("category") or "").strip()
    content = str(form.get("content") or "").strip()
    is_active = str(form.get("status") or "").strip() != "inactive"
    if not name or not category or not content:
        raise ValueError("Nama, kategori, dan isi pesan wajib diisi.")
    if category not in WA_TEMPLATE_CATEGORIES:
        raise ValueError("Kategori template tidak valid.")
    template.name = name
    template.category = category
    template.content = content
    template.sort_order = _parse_int(form.get("sort_order")) or _next_whatsapp_template_order()
    template.is_active = is_active
    template.updated_at = datetime.utcnow()


def next_whatsapp_template_order():
    max_order = db.session.query(func.max(WhatsAppTemplate.sort_order)).filter_by(is_deleted=False).scalar() or 0
    return max_order + 1


def _next_whatsapp_template_order():
    return next_whatsapp_template_order()


def _generate_whatsapp_template_key(name):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(name or "template"))
    base = "_".join(part for part in base.split("_") if part)[:50] or "template"
    key = base
    suffix = 2
    while WhatsAppTemplate.query.filter_by(key=key).first():
        key = f"{base}_{suffix}"
        suffix += 1
    return key


def send_lead_whatsapp(lead, template_id=None, message=None, user=None):
    return send_whatsapp_follow_up("Lead", lead, template_id, message, user)


def send_customer_whatsapp(customer, template_id=None, message=None, user=None):
    return send_whatsapp_follow_up("Customer", customer, template_id, message, user)


def send_whatsapp_follow_up(target_type, target, template_id=None, message=None, user=None):
    if not target:
        raise ValueError("Data tidak ditemukan.")
    phone = normalize_phone(getattr(target, "whatsapp", None))
    if not phone:
        raise ValueError("Nomor WhatsApp belum diisi.")
    if not phone.startswith("62"):
        raise ValueError("Nomor WhatsApp tidak valid.")
    template = None
    if str(template_id or "").isdigit():
        template = WhatsAppTemplate.query.filter_by(id=int(template_id), is_active=True, is_deleted=False).first()
    final_message = str(message or "").strip()
    if not final_message and template:
        final_message = render_whatsapp_template(template, target, target_type, user)
    if not final_message:
        raise ValueError("Isi pesan WhatsApp wajib diisi.")
    follow_up = FollowUp(
        follow_up_type=target_type,
        follow_up_date=date.today(),
        admin_id=user.id if user else None,
        admin_name=(user.name if user else None),
        content=final_message,
        status="Menunggu respon",
        notes=f"Dikirim via WhatsApp: {template.name if template else 'Custom'}",
    )
    if target_type == "Lead":
        follow_up.lead = target
    else:
        follow_up.customer = target
    db.session.add(follow_up)
    target.updated_at = datetime.utcnow()
    db.session.commit()
    return f"https://wa.me/{phone}?text={quote(final_message)}"


def render_whatsapp_template(template, target, target_type, user=None):
    values = {
        "name": getattr(target, "name", "") or "Kak",
        "brand": _target_brand_name(target),
        "cs_name": (user.name if user else None) or "Admin",
        "today": date.today().strftime("%d/%m/%Y"),
        "status": getattr(target, "status", "") or "-",
        "type": target_type,
        "need_type": getattr(target, "need_type", "") or "jersey",
        "estimated_qty": getattr(target, "estimated_qty", "") or "",
    }
    try:
        return template.content.format(**values)
    except KeyError:
        return template.content


def seed_default_whatsapp_templates():
    existing = {template.key: template for template in WhatsAppTemplate.query.filter_by(is_deleted=False).all()}
    for index, (key, name, category, content) in enumerate(DEFAULT_WA_TEMPLATES, start=1):
        template = existing.get(key)
        if not template:
            db.session.add(WhatsAppTemplate(key=key, name=name, category=category, content=content, sort_order=index, is_active=True))
        elif not template.sort_order:
            template.sort_order = index


def users_for_assignment():
    return User.query.filter_by(is_active=True).order_by(User.name.asc()).all()


def lead_form_data_for_sales_order(lead):
    source_label = lead.source
    if lead.source_detail:
        source_label = f"{source_label} - {lead.source_detail}"
    notes = []
    if lead.need_type:
        notes.append(f"Kebutuhan dari lead: {lead.need_type}")
    if lead.estimated_qty:
        notes.append(f"Estimasi qty: {lead.estimated_qty}")
    if lead.notes:
        notes.append(lead.notes)
    return {
        "lead_id": str(lead.id),
        "team_name": lead.name,
        "customer_name": lead.name,
        "customer_phone": lead.whatsapp or "",
        "customer_address": "",
        "customer_source": "Ahmad",
        "source_name": source_label,
        "notes": "\n".join(notes),
    }


def mark_lead_converted_for_order(order, form=None):
    lead_id = str((form or {}).get("lead_id") or "").strip()
    if not lead_id.isdigit():
        return None
    lead = Lead.query.get(int(lead_id))
    if not lead:
        return None
    lead.status = "Closing"
    lead.converted_so_id = order.id
    lead.converted_customer_id = order.crm_customer_id
    lead.updated_at = datetime.utcnow()
    return lead


def create_follow_up(form, user):
    follow_up_type = str(form.get("follow_up_type") or "Customer").strip()
    if follow_up_type not in ("Lead", "Customer"):
        raise ValueError("Tipe follow up tidak valid.")
    lead = None
    customer = None
    if follow_up_type == "Lead":
        lead_id = form.get("lead_id")
        if not str(lead_id or "").isdigit():
            raise ValueError("Lead wajib dipilih.")
        lead = get_lead(int(lead_id))
    else:
        customer_id = form.get("customer_id")
        if not str(customer_id or "").isdigit():
            raise ValueError("Customer wajib dipilih.")
        customer = get_customer(int(customer_id))
    status = str(form.get("status") or "").strip()
    if status not in FOLLOW_UP_STATUSES:
        raise ValueError("Status follow up tidak valid.")
    content = str(form.get("content") or "").strip()
    if not content:
        raise ValueError("Isi follow up wajib diisi.")
    follow_up = FollowUp(
        follow_up_type=follow_up_type,
        lead=lead,
        customer=customer,
        follow_up_date=_parse_date(form.get("follow_up_date")) or date.today(),
        admin_id=user.id if user else None,
        admin_name=(user.name if user else None) or str(form.get("admin_name") or "").strip() or None,
        content=content,
        customer_response=str(form.get("customer_response") or "").strip() or None,
        status=status,
        next_follow_up_date=_parse_date(form.get("next_follow_up_date")),
        notes=str(form.get("notes") or "").strip() or None,
    )
    db.session.add(follow_up)
    if customer:
        customer.updated_at = datetime.utcnow()
    if lead:
        lead.updated_at = datetime.utcnow()
    db.session.commit()
    return follow_up


def update_customer(customer, form):
    customer.name = str(form.get("name") or "").strip() or customer.name
    customer.whatsapp = str(form.get("whatsapp") or "").strip() or None
    customer.address = str(form.get("address") or "").strip() or None
    source = str(form.get("source") or "").strip()
    customer.source = source if source in CUSTOMER_SOURCES else customer.source
    customer.source_name = str(form.get("source_name") or "").strip() or None
    customer.status = str(form.get("status") or "").strip() or customer.status
    customer.character_notes = str(form.get("character_notes") or "").strip() or None
    refresh_customer_stats(customer)
    db.session.commit()
    return customer


def sync_sales_order_customer(order, form=None):
    if not order:
        return None
    form = form or {}
    customer_access = order.customer_access
    name = str(form.get("customer_name") or "").strip() or (customer_access.customer_name if customer_access else None) or order.team_name
    whatsapp = str(form.get("customer_phone") or "").strip() or (customer_access.customer_phone if customer_access else None)
    address = str(form.get("customer_address") or "").strip() or None
    source = _source_from_form(form, order)
    source_name = _source_name_from_form(form, order, source)
    customer = order.crm_customer or find_customer(name, whatsapp)
    if not customer:
        customer = Customer(name=name)
        db.session.add(customer)
    _apply_customer_identity(customer, name, whatsapp, address, source, source_name)
    order.crm_customer = customer
    refresh_customer_stats(customer)
    return customer


def sync_nota_customer(nota):
    if not nota:
        return None
    customer = nota.crm_customer or (nota.sales_order.crm_customer if nota.sales_order and nota.sales_order.crm_customer else None)
    if not customer:
        customer = find_customer(nota.customer.name, nota.customer.phone)
    if not customer:
        customer = Customer(name=nota.customer.name)
        db.session.add(customer)
    source = customer.source
    source_name = customer.source_name
    if nota.sales_order:
        source = _source_from_form({}, nota.sales_order)
        source_name = _source_name_from_form({}, nota.sales_order, source)
    _apply_customer_identity(customer, nota.customer.name, nota.customer.phone, nota.customer.address, source, source_name)
    nota.crm_customer = customer
    if nota.sales_order and not nota.sales_order.crm_customer:
        nota.sales_order.crm_customer = customer
    refresh_customer_stats(customer)
    return customer


def refresh_all_customer_stats():
    for customer in Customer.query.all():
        refresh_customer_stats(customer)
    db.session.commit()


def refresh_customer_stats(customer):
    db.session.flush()
    so_query = SalesOrder.query.filter(SalesOrder.crm_customer_id == customer.id, SalesOrder.is_deleted.is_(False))
    nota_query = Nota.query.filter(Nota.crm_customer_id == customer.id)
    customer.total_sales_orders = so_query.count()
    customer.total_notas = nota_query.count()
    first_so = so_query.order_by(SalesOrder.created_at.asc()).first()
    first_nota = nota_query.order_by(Nota.order_date.asc()).first()
    dates = []
    if first_so and first_so.created_at:
        dates.append(first_so.created_at.date())
    if first_nota and first_nota.order_date:
        dates.append(first_nota.order_date)
    customer.first_order_date = min(dates) if dates else customer.first_order_date
    customer.status = _customer_status(customer)
    customer.updated_at = datetime.utcnow()
    return customer


def crm_summary():
    today = date.today()
    month_start = today.replace(day=1)
    new_this_month = Customer.query.filter(Customer.created_at >= datetime.combine(month_start, datetime.min.time())).count()
    repeat_this_month = (
        Customer.query.join(SalesOrder)
        .filter(Customer.total_sales_orders > 1, SalesOrder.created_at >= datetime.combine(month_start, datetime.min.time()))
        .distinct()
        .count()
    )
    due_today = FollowUp.query.filter(FollowUp.next_follow_up_date == today, FollowUp.status.notin_(("Closing", "Tidak jadi"))).count()
    open_follow_ups = FollowUp.query.filter(FollowUp.status.notin_(("Closing", "Tidak jadi"))).count()
    top_source_row = (
        db.session.query(Customer.source, func.count(Customer.id).label("total"))
        .group_by(Customer.source)
        .order_by(func.count(Customer.id).desc(), Customer.source.asc())
        .first()
    )
    top_customers = Customer.query.order_by(Customer.total_sales_orders.desc(), Customer.total_notas.desc(), Customer.name.asc()).limit(5).all()
    lead_new_this_month = Lead.query.filter(Lead.created_at >= datetime.combine(month_start, datetime.min.time())).count()
    lead_unreplied = Lead.query.filter(Lead.status == "Baru masuk").count()
    lead_follow_up_today = Lead.query.filter(Lead.next_follow_up_date == today, Lead.status.notin_(("Closing", "Tidak jadi"))).count()
    lead_closing_this_month = Lead.query.filter(
        Lead.status == "Closing",
        Lead.updated_at >= datetime.combine(month_start, datetime.min.time()),
    ).count()
    total_leads = Lead.query.count()
    converted_leads = Lead.query.filter(Lead.converted_so_id.isnot(None)).count()
    conversion_rate = round((converted_leads / total_leads) * 100, 1) if total_leads else 0
    return {
        "new_this_month": new_this_month,
        "repeat_this_month": repeat_this_month,
        "due_today": due_today,
        "open_follow_ups": open_follow_ups,
        "top_source": top_source_row,
        "top_customers": top_customers,
        "lead_new_this_month": lead_new_this_month,
        "lead_unreplied": lead_unreplied,
        "lead_follow_up_today": lead_follow_up_today,
        "lead_closing_this_month": lead_closing_this_month,
        "lead_conversion_rate": conversion_rate,
    }


def find_customer(name, whatsapp=None):
    normalized_phone = normalize_phone(whatsapp)
    if normalized_phone:
        for customer in Customer.query.filter(Customer.whatsapp.isnot(None)).all():
            if normalize_phone(customer.whatsapp) == normalized_phone:
                return customer
    clean_name = " ".join(str(name or "").split())
    if clean_name:
        return Customer.query.filter(func.lower(Customer.name) == clean_name.lower()).first()
    return None


def _apply_customer_identity(customer, name, whatsapp, address, source, source_name):
    customer.name = name or customer.name
    if whatsapp:
        customer.whatsapp = whatsapp
    if address:
        customer.address = address
    customer.source = source if source in CUSTOMER_SOURCES else (customer.source or "Ahmad")
    customer.source_name = source_name or customer.source_name


def _source_from_form(form, order):
    source = str(form.get("customer_source") or "").strip()
    if source in CUSTOMER_SOURCES:
        return source
    if order and order.is_evpro_brand:
        return "Reseller EVPRO" if order.seller_name else "Ahmad"
    return "Brand"


def _source_name_from_form(form, order, source):
    value = str(form.get("source_name") or "").strip()
    if value:
        return value
    if source == "Reseller EVPRO" and order:
        return order.seller_name
    if source == "Brand" and order and order.brand:
        return order.brand.name
    return None


def _customer_status(customer):
    if int(customer.total_sales_orders or 0) > 1:
        return "Repeat"
    if int(customer.total_sales_orders or 0) == 1 or int(customer.total_notas or 0) > 0:
        return "Aktif"
    return customer.status if customer.status == "Pasif" else "Baru"


def _fill_lead(lead, form, user=None):
    name = str(form.get("name") or "").strip()
    if not name:
        raise ValueError("Nama lead wajib diisi.")
    source = str(form.get("source") or "").strip()
    status = str(form.get("status") or "").strip()
    if source not in LEAD_SOURCES:
        raise ValueError("Sumber lead tidak valid.")
    if status not in LEAD_STATUSES:
        raise ValueError("Status lead tidak valid.")
    assigned_to = form.get("assigned_to")
    lead.name = name
    lead.whatsapp = str(form.get("whatsapp") or "").strip() or None
    lead.source = source
    lead.source_detail = str(form.get("source_detail") or "").strip() or None
    lead.need_type = str(form.get("need_type") or "").strip() or None
    lead.estimated_qty = _parse_int(form.get("estimated_qty"))
    lead.notes = str(form.get("notes") or "").strip() or None
    lead.status = status
    lead.next_follow_up_date = _parse_date(form.get("next_follow_up_date"))
    if str(assigned_to or "").isdigit():
        lead.assigned_to = int(assigned_to)
    elif user and not lead.assigned_to:
        lead.assigned_to = user.id
    lead.updated_at = datetime.utcnow()
    return lead


def _parse_int(value):
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _target_brand_name(target):
    source_name = str(getattr(target, "source_name", "") or getattr(target, "source_detail", "") or "").strip()
    if source_name:
        return source_name
    return "EVPRO"


def _parse_date(value):
    if isinstance(value, date):
        return value
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
