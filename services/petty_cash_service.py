import re
from datetime import date, datetime
from io import BytesIO
from types import SimpleNamespace

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import case, func, or_
from sqlalchemy.orm import joinedload

from database.db import db
from models import NotaPayment, User
from models.petty_cash import AllowanceReserve, EmployeeCashAdvance, ExpenseCategoryGroup, FinancialAuditLog, PettyCashCategory, PettyCashTransaction
from services.nota_service import display_nota_number
from services.sort_order_service import get_next_sort_order
from utils.formatters import pretty_date, rupiah


TRANSACTION_IN = "IN"
TRANSACTION_OUT = "OUT"
SOURCE_NOTA_PAYMENT = "NOTA_PAYMENT"
SOURCE_OPENING_BALANCE = "OPENING_BALANCE"
SOURCE_CAPITAL_ADDITION = "CAPITAL_ADDITION"
SOURCE_OFFLINE_SALE = "OFFLINE_SALE"
SOURCE_MANUAL_INCOME = "MANUAL_INCOME"
SOURCE_EMPLOYEE_CASH_ADVANCE = "EMPLOYEE_CASH_ADVANCE"
SOURCE_EMPLOYEE_CASH_ADVANCE_RETURN = "EMPLOYEE_CASH_ADVANCE_RETURN"
SOURCE_ALLOWANCE_RESERVE = "ALLOWANCE_RESERVE"
SOURCE_TRANSFER_TO_MAIN_CASH = "TRANSFER_TO_MAIN_CASH"
SOURCE_OWNER_WITHDRAWAL = "OWNER_WITHDRAWAL"
SOURCE_OPERATING_EXPENSE = "OPERATING_EXPENSE"

CATEGORY_TYPE_LABELS = {
    SOURCE_OPERATING_EXPENSE: "Biaya Operasional",
    SOURCE_EMPLOYEE_CASH_ADVANCE: "Kasbon",
    SOURCE_ALLOWANCE_RESERVE: "Penyisihan Tunjangan",
    SOURCE_TRANSFER_TO_MAIN_CASH: "Transfer ke Kas Besar",
    SOURCE_OWNER_WITHDRAWAL: "Prive",
}

MONTH_OPTIONS = [
    (1, "Januari"),
    (2, "Februari"),
    (3, "Maret"),
    (4, "April"),
    (5, "Mei"),
    (6, "Juni"),
    (7, "Juli"),
    (8, "Agustus"),
    (9, "September"),
    (10, "Oktober"),
    (11, "November"),
    (12, "Desember"),
]

INCOME_SOURCES = {
    SOURCE_OPENING_BALANCE: "Saldo Awal",
    SOURCE_CAPITAL_ADDITION: "Penambahan Modal",
    SOURCE_OFFLINE_SALE: "Penjualan Offline",
    SOURCE_NOTA_PAYMENT: "Pembayaran Nota Cash",
    SOURCE_EMPLOYEE_CASH_ADVANCE_RETURN: "Pengembalian Kasbon Secara Tunai",
    SOURCE_MANUAL_INCOME: "Pemasukan Lainnya",
}

DEFAULT_CATEGORIES = [
    ("Produksi dan Packaging", "Packaging Produk", "PROD_PACKAGING", SOURCE_OPERATING_EXPENSE, True),
    ("Produksi dan Packaging", "Bahan Sablon", "PROD_SCREEN_PRINT", SOURCE_OPERATING_EXPENSE, True),
    ("Produksi dan Packaging", "Bahan Pendukung Produksi", "PROD_SUPPORT_MATERIAL", SOURCE_OPERATING_EXPENSE, True),
    ("Produksi dan Packaging", "Alat Pendukung Produksi", "PROD_SUPPORT_TOOL", SOURCE_OPERATING_EXPENSE, True),
    ("Produksi dan Packaging", "Perlengkapan Produksi", "PROD_SUPPLIES", SOURCE_OPERATING_EXPENSE, True),
    ("Produksi dan Packaging", "Pengeluaran Produksi Lainnya", "PROD_OTHER", SOURCE_OPERATING_EXPENSE, True),
    ("Transportasi dan Logistik", "Transportasi Pengambilan Barang", "LOG_PICKUP", SOURCE_OPERATING_EXPENSE, True),
    ("Transportasi dan Logistik", "Pengiriman Barang", "LOG_SHIPPING", SOURCE_OPERATING_EXPENSE, True),
    ("Transportasi dan Logistik", "Bensin Operasional", "LOG_FUEL", SOURCE_OPERATING_EXPENSE, True),
    ("Transportasi dan Logistik", "Parkir dan Tol", "LOG_PARKING_TOLL", SOURCE_OPERATING_EXPENSE, True),
    ("Transportasi dan Logistik", "Biaya Perjalanan Operasional", "LOG_TRAVEL", SOURCE_OPERATING_EXPENSE, True),
    ("Transportasi dan Logistik", "Logistik Lainnya", "LOG_OTHER", SOURCE_OPERATING_EXPENSE, True),
    ("Gaji, Upah, dan Insentif", "Upah Karyawan Mingguan", "PAY_WEEKLY_WAGE", SOURCE_OPERATING_EXPENSE, True),
    ("Gaji, Upah, dan Insentif", "Upah Tambahan", "PAY_EXTRA_WAGE", SOURCE_OPERATING_EXPENSE, True),
    ("Gaji, Upah, dan Insentif", "Uang Lembur", "PAY_OVERTIME", SOURCE_OPERATING_EXPENSE, True),
    ("Gaji, Upah, dan Insentif", "Bonus Seller", "PAY_SELLER_BONUS", SOURCE_OPERATING_EXPENSE, True),
    ("Gaji, Upah, dan Insentif", "Bonus Karyawan", "PAY_EMPLOYEE_BONUS", SOURCE_OPERATING_EXPENSE, True),
    ("Gaji, Upah, dan Insentif", "Honor Tenaga Tambahan", "PAY_EXTRA_LABOR", SOURCE_OPERATING_EXPENSE, True),
    ("Gaji, Upah, dan Insentif", "Insentif Lainnya", "PAY_OTHER", SOURCE_OPERATING_EXPENSE, True),
    ("Konsumsi dan Kegiatan Karyawan", "Makan Karyawan", "MEAL_EMPLOYEE", SOURCE_OPERATING_EXPENSE, True),
    ("Konsumsi dan Kegiatan Karyawan", "Minum Karyawan", "MEAL_DRINK", SOURCE_OPERATING_EXPENSE, True),
    ("Konsumsi dan Kegiatan Karyawan", "Konsumsi Meeting", "MEAL_MEETING", SOURCE_OPERATING_EXPENSE, True),
    ("Konsumsi dan Kegiatan Karyawan", "Uang Meeting", "MEAL_MEETING_ALLOWANCE", SOURCE_OPERATING_EXPENSE, True),
    ("Konsumsi dan Kegiatan Karyawan", "Kegiatan Internal Karyawan", "MEAL_INTERNAL_ACTIVITY", SOURCE_OPERATING_EXPENSE, True),
    ("Konsumsi dan Kegiatan Karyawan", "Konsumsi Lainnya", "MEAL_OTHER", SOURCE_OPERATING_EXPENSE, True),
    ("Administrasi dan Perkantoran", "Alat Tulis Kantor", "ADM_STATIONERY", SOURCE_OPERATING_EXPENSE, True),
    ("Administrasi dan Perkantoran", "Fotokopi dan Percetakan", "ADM_PRINT_COPY", SOURCE_OPERATING_EXPENSE, True),
    ("Administrasi dan Perkantoran", "Materai", "ADM_STAMP", SOURCE_OPERATING_EXPENSE, True),
    ("Administrasi dan Perkantoran", "Perlengkapan Kantor", "ADM_OFFICE_SUPPLIES", SOURCE_OPERATING_EXPENSE, True),
    ("Administrasi dan Perkantoran", "Biaya Administrasi", "ADM_FEE", SOURCE_OPERATING_EXPENSE, True),
    ("Administrasi dan Perkantoran", "Administrasi Lainnya", "ADM_OTHER", SOURCE_OPERATING_EXPENSE, True),
    ("Sewa dan Utilitas", "Sewa Rumah atau Tempat Usaha", "UTIL_RENT", SOURCE_OPERATING_EXPENSE, True),
    ("Sewa dan Utilitas", "Listrik", "UTIL_ELECTRICITY", SOURCE_OPERATING_EXPENSE, True),
    ("Sewa dan Utilitas", "Air", "UTIL_WATER", SOURCE_OPERATING_EXPENSE, True),
    ("Sewa dan Utilitas", "Internet", "UTIL_INTERNET", SOURCE_OPERATING_EXPENSE, True),
    ("Sewa dan Utilitas", "Kebersihan", "UTIL_CLEANING", SOURCE_OPERATING_EXPENSE, True),
    ("Sewa dan Utilitas", "Utilitas Lainnya", "UTIL_OTHER", SOURCE_OPERATING_EXPENSE, True),
    ("Pemeliharaan dan Perbaikan", "Maintenance Mesin Mingguan", "MAINT_WEEKLY_MACHINE", SOURCE_OPERATING_EXPENSE, True),
    ("Pemeliharaan dan Perbaikan", "Servis Mesin", "MAINT_MACHINE_SERVICE", SOURCE_OPERATING_EXPENSE, True),
    ("Pemeliharaan dan Perbaikan", "Spare Part Mesin", "MAINT_SPARE_PART", SOURCE_OPERATING_EXPENSE, True),
    ("Pemeliharaan dan Perbaikan", "Perbaikan Alat Kerja", "MAINT_WORK_TOOL", SOURCE_OPERATING_EXPENSE, True),
    ("Pemeliharaan dan Perbaikan", "Maintenance Kendaraan", "MAINT_VEHICLE", SOURCE_OPERATING_EXPENSE, True),
    ("Pemeliharaan dan Perbaikan", "Pemeliharaan Lainnya", "MAINT_OTHER", SOURCE_OPERATING_EXPENSE, True),
    ("Kasbon Karyawan", "Pemberian Kasbon", "ADVANCE_GIVE", SOURCE_EMPLOYEE_CASH_ADVANCE, False),
    ("Kasbon Karyawan", "Tambahan Kasbon", "ADVANCE_ADD", SOURCE_EMPLOYEE_CASH_ADVANCE, False),
    ("Kasbon Karyawan", "Koreksi Kasbon", "ADVANCE_CORRECTION", SOURCE_EMPLOYEE_CASH_ADVANCE, False),
    ("Penyisihan Tunjangan", "Penyisihan THR", "ALLOW_THR", SOURCE_ALLOWANCE_RESERVE, False),
    ("Penyisihan Tunjangan", "Penyisihan Tunjangan Akhir Tahun", "ALLOW_YEAR_END", SOURCE_ALLOWANCE_RESERVE, False),
    ("Penyisihan Tunjangan", "Penyisihan Bonus Tahunan", "ALLOW_ANNUAL_BONUS", SOURCE_ALLOWANCE_RESERVE, False),
    ("Penyisihan Tunjangan", "Penyisihan Dana Kesejahteraan", "ALLOW_WELFARE", SOURCE_ALLOWANCE_RESERVE, False),
    ("Penyisihan Tunjangan", "Penyisihan Tunjangan Lainnya", "ALLOW_OTHER", SOURCE_ALLOWANCE_RESERVE, False),
    ("Transfer ke Kas Besar", "Setoran Tunai ke Rekening Perusahaan", "TRANSFER_COMPANY_ACCOUNT", SOURCE_TRANSFER_TO_MAIN_CASH, False),
    ("Transfer ke Kas Besar", "Transfer ke Rekening Operasional", "TRANSFER_OPERATIONAL_ACCOUNT", SOURCE_TRANSFER_TO_MAIN_CASH, False),
    ("Transfer ke Kas Besar", "Pemindahan ke Kas Besar", "TRANSFER_MAIN_CASH", SOURCE_TRANSFER_TO_MAIN_CASH, False),
    ("Transfer ke Kas Besar", "Transfer Internal Lainnya", "TRANSFER_OTHER", SOURCE_TRANSFER_TO_MAIN_CASH, False),
    ("Prive/Pengambilan Pemilik", "Pengambilan Pribadi Pemilik", "OWNER_PERSONAL", SOURCE_OWNER_WITHDRAWAL, False),
    ("Prive/Pengambilan Pemilik", "Kebutuhan Rumah Pribadi", "OWNER_HOME", SOURCE_OWNER_WITHDRAWAL, False),
    ("Prive/Pengambilan Pemilik", "Keperluan Keluarga", "OWNER_FAMILY", SOURCE_OWNER_WITHDRAWAL, False),
    ("Prive/Pengambilan Pemilik", "Prive Lainnya", "OWNER_OTHER", SOURCE_OWNER_WITHDRAWAL, False),
    ("Pengeluaran Lainnya", "Pengeluaran Lainnya", "OTHER_EXPENSE", SOURCE_OPERATING_EXPENSE, True),
]

DEFAULT_GROUP_PREFIXES = {
    "Produksi dan Packaging": "PROD",
    "Transportasi dan Logistik": "LOG",
    "Gaji, Upah, dan Insentif": "PAY",
    "Konsumsi dan Kegiatan Karyawan": "MEAL",
    "Administrasi dan Perkantoran": "ADM",
    "Sewa dan Utilitas": "UTIL",
    "Pemeliharaan dan Perbaikan": "MAINT",
    "Kasbon Karyawan": "ADVANCE",
    "Penyisihan Tunjangan": "ALLOW",
    "Transfer ke Kas Besar": "TRANSFER",
    "Prive/Pengambilan Pemilik": "OWNER",
    "Pengeluaran Lainnya": "OTHER",
    "Operasional Kantor": "OPS",
    "Transportasi": "TRANS",
    "Karyawan": "EMP",
    "Marketing": "MKT",
    "Tunjangan": "ALLOWANCE",
    "Lainnya": "OTHER",
}


def seed_default_petty_cash_categories():
    _sync_expense_category_groups()
    existing = {row.category_code: row for row in PettyCashCategory.query.all()}
    for index, (group, name, code, category_type, operational) in enumerate(DEFAULT_CATEGORIES, start=1):
        group_row = _ensure_expense_category_group(group, sort_order=index)
        category = existing.get(code)
        if not category:
            category = PettyCashCategory(
                category_code=code,
                group=group_row,
                group_name=group_row.name,
                category_name=name,
                category_type=category_type,
                is_operational_expense=operational,
                sort_order=_next_category_sort_order_for_group(group_row),
            )
            db.session.add(category)
        else:
            category.group = category.group or group_row
            category.group_name = category.group_name or group_row.name
            category.category_name = category.category_name or name
            category.category_type = category.category_type or category_type
    _backfill_expense_category_metadata()
    db.session.commit()
    _sync_category_group_ids()


def categories(active_only=False):
    query = PettyCashCategory.query.outerjoin(ExpenseCategoryGroup)
    if active_only:
        query = query.filter(PettyCashCategory.is_active.is_(True))
    return query.order_by(
        func.coalesce(ExpenseCategoryGroup.sort_order, 2147483647).asc(),
        PettyCashCategory.group_name.asc(),
        func.coalesce(PettyCashCategory.sort_order, 0).asc(),
        PettyCashCategory.category_name.asc(),
    ).all()


def category_groups(active_only=False):
    rows = categories(active_only=active_only)
    grouped = {}
    for category in rows:
        grouped.setdefault(category.group_name, []).append(category)
    return grouped


def expense_category_groups(active_only=False):
    _sync_expense_category_groups()
    query = ExpenseCategoryGroup.query
    if active_only:
        query = query.filter(ExpenseCategoryGroup.is_active.is_(True))
    return query.order_by(ExpenseCategoryGroup.sort_order.asc(), ExpenseCategoryGroup.name.asc()).all()


def suggested_category_code(form):
    group, _, _ = _resolve_category_group(form, persist=False)
    category_name = _clean_label(form.get("category_name"))
    if not group or not category_name:
        return ""
    return _unique_category_code(group.code_prefix, category_name, None)


def suggested_category_sort_order(form):
    group, _, _ = _resolve_category_group(form, persist=False)
    if not group:
        return _next_category_sort_order_for_new_group()
    return _next_category_sort_order_for_group(group)


def _sync_expense_category_groups():
    sort_lookup = {}
    for index, (group_name, _, _, _, _) in enumerate(DEFAULT_CATEGORIES, start=1):
        sort_lookup.setdefault(_normalize_label(group_name), index)
        _ensure_expense_category_group(group_name, sort_order=index)
    existing_names = [
        row[0]
        for row in db.session.query(PettyCashCategory.group_name)
        .filter(PettyCashCategory.group_name.isnot(None), PettyCashCategory.group_name != "")
        .distinct()
        .all()
    ]
    for group_name in existing_names:
        _ensure_expense_category_group(group_name, sort_order=sort_lookup.get(_normalize_label(group_name), 999))
    db.session.flush()
    _sync_category_group_ids()
    db.session.commit()


def _sync_category_group_ids():
    groups = {group.normalized_name: group for group in ExpenseCategoryGroup.query.all()}
    for category in PettyCashCategory.query.filter(PettyCashCategory.group_name.isnot(None)).all():
        group = groups.get(_normalize_label(category.group_name))
        if group:
            category.group = group
            category.group_name = group.name


def _backfill_expense_category_metadata():
    next_orders = {}
    rows = PettyCashCategory.query.order_by(PettyCashCategory.id.asc()).all()
    for category in rows:
        group_key = category.group_id or _normalize_label(category.group_name)
        if category.sort_order and category.sort_order > 0:
            next_orders[group_key] = max(next_orders.get(group_key, 0), category.sort_order)

    for category in rows:
        group = category.group
        if not category.category_code and group:
            category.category_code = _unique_category_code(group.code_prefix, category.category_name, category.id)
        if not category.sort_order or category.sort_order < 1:
            group_key = category.group_id or _normalize_label(category.group_name)
            next_orders[group_key] = next_orders.get(group_key, 0) + 1
            category.sort_order = next_orders[group_key]


def _ensure_expense_category_group(group_name, code_prefix=None, sort_order=0):
    name = _clean_label(group_name)
    normalized = _normalize_label(name)
    if not normalized:
        return None
    existing = ExpenseCategoryGroup.query.filter(ExpenseCategoryGroup.normalized_name == normalized).first()
    if existing:
        if code_prefix:
            prefix = _normalize_prefix(code_prefix)
            if prefix and prefix != existing.code_prefix:
                duplicate = ExpenseCategoryGroup.query.filter(ExpenseCategoryGroup.code_prefix == prefix, ExpenseCategoryGroup.id != existing.id).first()
                if duplicate:
                    raise ValueError("Prefix kelompok sudah digunakan.")
                existing.code_prefix = prefix
        existing.name = name
        existing.sort_order = existing.sort_order or sort_order
        return existing

    prefix = _normalize_prefix(code_prefix) or DEFAULT_GROUP_PREFIXES.get(name) or _suggest_group_prefix(name)
    prefix = _unique_group_prefix(prefix)
    group = ExpenseCategoryGroup(
        name=name,
        normalized_name=normalized,
        code_prefix=prefix,
        sort_order=sort_order,
        is_active=True,
    )
    db.session.add(group)
    return group


def _resolve_category_group(form, persist=False):
    group_raw = str(form.get("group_id") or "").strip()
    group_id = _parse_int(group_raw)
    selection = str(form.get("group_select") or "").strip()
    wants_new = group_raw == "__new__" or selection == "__new__" or str(form.get("new_group_name") or "").strip()
    if wants_new:
        name = _clean_label(form.get("new_group_name"))
        prefix = _normalize_prefix(form.get("new_group_prefix"))
        if not name:
            return None, True, "Nama Kelompok Baru wajib diisi."
        if not prefix:
            return None, True, "Prefix kelompok wajib diisi."
        existing_name = ExpenseCategoryGroup.query.filter(ExpenseCategoryGroup.normalized_name == _normalize_label(name)).first()
        if existing_name:
            return None, True, "Kelompok tersebut sudah tersedia."
        existing_prefix = ExpenseCategoryGroup.query.filter(ExpenseCategoryGroup.code_prefix == prefix).first()
        if existing_prefix:
            return None, True, "Prefix kelompok sudah digunakan."
        if not persist:
            return _row(id=None, name=name, code_prefix=prefix), True, None
        group = _ensure_expense_category_group(name, code_prefix=prefix, sort_order=_next_expense_group_sort_order())
        return group, True, None

    if group_id:
        group = ExpenseCategoryGroup.query.get(group_id)
        if group:
            return group, False, None
    legacy_name = _clean_label(form.get("group_name"))
    if legacy_name:
        group = ExpenseCategoryGroup.query.filter(ExpenseCategoryGroup.normalized_name == _normalize_label(legacy_name)).first()
        if group:
            return group, False, None
    return None, False, "Kelompok wajib dipilih."


def _validate_duplicate_subcategory(group, category_name, category_id=None):
    normalized_name = _normalize_label(category_name)
    for row in PettyCashCategory.query.filter(PettyCashCategory.id != (category_id or 0)).all():
        same_group_id = row.group_id and group.id and row.group_id == group.id
        same_group_name = _normalize_label(row.group_name) == group.normalized_name
        if (same_group_id or same_group_name) and _normalize_label(row.category_name) == normalized_name:
            raise ValueError("Subkategori tersebut sudah tersedia pada kelompok yang dipilih.")


def _unique_category_code(group_prefix, category_name, category_id=None):
    base = f"{_normalize_prefix(group_prefix)}_{_slug_code(category_name)}".strip("_")
    if not base:
        base = "CATEGORY"
    code = base
    sequence = 2
    while PettyCashCategory.query.filter(PettyCashCategory.category_code == code, PettyCashCategory.id != (category_id or 0)).first():
        code = f"{base}_{sequence}"
        sequence += 1
    return code


def _next_category_sort_order_for_group(group):
    if not group or not getattr(group, "id", None):
        return _next_category_sort_order_for_new_group()
    return get_next_sort_order(PettyCashCategory, {"group_id": group.id})


def _next_category_sort_order_for_new_group():
    return 1


def _unique_group_prefix(prefix):
    base = _normalize_prefix(prefix) or "GROUP"
    value = base
    sequence = 2
    while ExpenseCategoryGroup.query.filter_by(code_prefix=value).first():
        value = f"{base}{sequence}"
        sequence += 1
    return value


def _next_expense_group_sort_order():
    return get_next_sort_order(ExpenseCategoryGroup)


def _suggest_group_prefix(group_name):
    words = [word for word in re.split(r"[^A-Za-z0-9]+", _strip_accents(group_name).upper()) if word and word not in {"DAN", "YANG", "KE"}]
    if not words:
        return "GROUP"
    if len(words) == 1:
        return words[0][:8]
    return "".join(word[:2] for word in words)[:8]


def _slug_code(value):
    text_value = _strip_accents(value).upper()
    text_value = re.sub(r"[^A-Z0-9]+", "_", text_value)
    text_value = re.sub(r"_+", "_", text_value).strip("_")
    return text_value[:40] or "CATEGORY"


def _normalize_prefix(value):
    return re.sub(r"[^A-Z0-9]", "", _strip_accents(value).upper())


def _normalize_label(value):
    return " ".join(str(value or "").strip().casefold().split())


def _clean_label(value):
    return " ".join(str(value or "").strip().split())


def _strip_accents(value):
    return str(value or "").encode("ascii", "ignore").decode("ascii")


def transaction_year_options(today=None):
    today = today or date.today()
    years = {today.year}
    rows = db.session.query(func.strftime("%Y", PettyCashTransaction.transaction_date)).filter(
        PettyCashTransaction.transaction_date.isnot(None)
    ).distinct().all()
    for year, in rows:
        if str(year or "").isdigit():
            years.add(int(year))
    return sorted(years, reverse=True)


def current_balance():
    income = _sum_transactions(TRANSACTION_IN)
    expense = _sum_transactions(TRANSACTION_OUT)
    return income - expense


def dashboard_data(today=None):
    today = today or date.today()
    start = today.replace(day=1)
    month_transactions = _active_query().filter(PettyCashTransaction.transaction_date >= start, PettyCashTransaction.transaction_date <= today).all()
    expenses = [row for row in month_transactions if row.transaction_type == TRANSACTION_OUT]
    return {
        "balance": current_balance(),
        "month_income": sum(row.amount for row in month_transactions if row.transaction_type == TRANSACTION_IN),
        "month_expense": sum(row.amount for row in expenses),
        "month_count": len(month_transactions),
        "latest": _active_query().order_by(PettyCashTransaction.transaction_date.desc(), PettyCashTransaction.created_at.desc(), PettyCashTransaction.id.desc()).limit(10).all(),
        "expense_summary": expense_summary(expenses),
    }


def expense_summary(transactions=None):
    transactions = transactions if transactions is not None else _active_query().filter(PettyCashTransaction.transaction_type == TRANSACTION_OUT).all()
    summary = {
        SOURCE_OPERATING_EXPENSE: 0,
        SOURCE_EMPLOYEE_CASH_ADVANCE: 0,
        SOURCE_ALLOWANCE_RESERVE: 0,
        SOURCE_TRANSFER_TO_MAIN_CASH: 0,
        SOURCE_OWNER_WITHDRAWAL: 0,
    }
    by_group = {}
    for trx in transactions:
        category = trx.category
        key = category.category_type if category else trx.source_type
        if category and category.is_operational_expense:
            key = SOURCE_OPERATING_EXPENSE
        if key in summary:
            summary[key] += trx.amount
        group = category.group_name if category else "Tanpa Kategori"
        by_group[group] = by_group.get(group, 0) + trx.amount
    return {"types": summary, "groups": by_group}


def create_income(form, user, file_storage=None):
    transaction_date = _parse_date(form.get("transaction_date"))
    amount = _parse_int(form.get("amount"))
    source_type = str(form.get("source_type") or "").strip()
    if not transaction_date:
        raise ValueError("Tanggal transaksi wajib diisi.")
    if amount <= 0:
        raise ValueError("Nominal wajib lebih dari nol.")
    if source_type not in INCOME_SOURCES or source_type == SOURCE_NOTA_PAYMENT:
        raise ValueError("Sumber pemasukan tidak valid.")
    trx = PettyCashTransaction(
        transaction_number=generate_transaction_number(TRANSACTION_IN, transaction_date),
        transaction_date=transaction_date,
        transaction_type=TRANSACTION_IN,
        amount=amount,
        source_type=source_type,
        reference_number=str(form.get("reference_number") or "").strip() or None,
        recipient=None,
        description=str(form.get("description") or "").strip() or None,
        attachment_path=_save_attachment(file_storage),
        created_by=user.id if user else None,
    )
    db.session.add(trx)
    audit("petty_cash_transaction", None, "created", new_value=f"{trx.transaction_number} {trx.amount}", user=user)
    db.session.commit()
    return trx


def create_expense(form, user, file_storage=None):
    transaction_date = _parse_date(form.get("transaction_date"))
    amount = _parse_int(form.get("amount"))
    category = PettyCashCategory.query.get(_parse_int(form.get("category_id")))
    description = str(form.get("description") or "").strip()
    if not transaction_date:
        raise ValueError("Tanggal pengeluaran wajib diisi.")
    if amount <= 0:
        raise ValueError("Nominal wajib lebih dari nol.")
    if not category or not category.is_active:
        raise ValueError("Subkategori wajib dipilih.")
    if not description:
        raise ValueError("Keterangan wajib diisi.")
    if amount > current_balance():
        raise ValueError("Saldo kas kecil tidak mencukupi untuk pengeluaran ini.")
    trx = PettyCashTransaction(
        transaction_number=generate_transaction_number(TRANSACTION_OUT, transaction_date),
        transaction_date=transaction_date,
        transaction_type=TRANSACTION_OUT,
        category=category,
        amount=amount,
        source_type=category.category_type,
        reference_number=str(form.get("reference_number") or "").strip() or None,
        recipient=str(form.get("recipient") or "").strip() or None,
        description=description,
        attachment_path=_save_attachment(file_storage),
        created_by=user.id if user else None,
    )
    db.session.add(trx)
    if category.category_type == SOURCE_EMPLOYEE_CASH_ADVANCE:
        db.session.add(EmployeeCashAdvance(
            transaction=trx,
            employee_name=str(form.get("employee_name") or "").strip() or str(form.get("recipient") or "").strip() or "-",
            advance_date=_parse_date(form.get("advance_date")) or transaction_date,
            amount=amount,
            status=str(form.get("advance_status") or "Belum Dipotong").strip(),
            settlement_date=_parse_date(form.get("settlement_date")),
            settlement_method=str(form.get("settlement_method") or "").strip() or None,
            notes=str(form.get("advance_notes") or "").strip() or description,
            created_by=user.id if user else None,
        ))
    if category.category_type == SOURCE_ALLOWANCE_RESERVE:
        db.session.add(AllowanceReserve(
            transaction=trx,
            allowance_type=str(form.get("allowance_type") or category.category_name).strip(),
            allowance_period=str(form.get("allowance_period") or "").strip() or None,
            destination_account=str(form.get("destination_account") or "").strip() or None,
            amount=amount,
            notes=str(form.get("allowance_notes") or "").strip() or description,
        ))
    audit("petty_cash_transaction", None, "created", new_value=f"{trx.transaction_number} {trx.amount}", user=user)
    db.session.commit()
    return trx


def upsert_category(form):
    category_id = _parse_int(form.get("category_id"))
    category = PettyCashCategory.query.get(category_id) if category_id else None
    existing_category = bool(category)
    group, is_new_group, group_error = _resolve_category_group(form, persist=True)
    category_name = _clean_label(form.get("category_name"))
    if group_error:
        raise ValueError(group_error)
    if not group or not category_name:
        raise ValueError("Kelompok dan subkategori wajib diisi.")
    _validate_duplicate_subcategory(group, category_name, category.id if category else None)

    category_is_used = existing_category and PettyCashTransaction.query.filter_by(category_id=category.id).first() is not None
    group_changed = existing_category and category.group_id and category.group_id != group.id
    name_changed = existing_category and _normalize_label(category.category_name) != _normalize_label(category_name)
    generated_code = None
    if not existing_category or (not category_is_used and (group_changed or name_changed)):
        generated_code = _unique_category_code(group.code_prefix, category_name, category.id if category else None)

    generated_sort_order = category.sort_order if existing_category else None
    if not existing_category or not generated_sort_order or generated_sort_order < 1:
        generated_sort_order = _next_category_sort_order_for_group(group)

    if not category:
        category = PettyCashCategory(category_code=generated_code)
        db.session.add(category)
    elif generated_code:
        category.category_code = generated_code

    category.group = group
    category.group_name = group.name
    category.category_name = category_name
    category.category_type = str(form.get("category_type") or SOURCE_OPERATING_EXPENSE).strip()
    category.is_operational_expense = bool(form.get("is_operational_expense"))
    category.is_active = bool(form.get("is_active"))
    category.sort_order = generated_sort_order
    db.session.commit()
    return category


def set_category_active(category_id, active=True):
    category = PettyCashCategory.query.get_or_404(category_id)
    category.is_active = bool(active)
    db.session.commit()
    return category


def void_transaction(transaction_id, reason, user):
    reason = str(reason or "").strip()
    if not reason:
        raise ValueError("Alasan pembatalan wajib diisi.")
    trx = PettyCashTransaction.query.get_or_404(transaction_id)
    if trx.source_type == SOURCE_NOTA_PAYMENT:
        raise ValueError("Transaksi dari pembayaran Nota harus dibatalkan dari halaman Nota.")
    if trx.is_void:
        return trx
    trx.is_void = True
    trx.void_reason = reason
    trx.voided_by = user.id if user else None
    trx.voided_at = datetime.utcnow()
    audit("petty_cash_transaction", trx.id, "voided", old_value=trx.transaction_number, new_value=reason, user=user)
    db.session.commit()
    return trx


def sync_nota_payment_cash_transaction(payment, user=None):
    existing = PettyCashTransaction.query.filter_by(source_type=SOURCE_NOTA_PAYMENT, source_id=payment.id).first()
    is_cash = (payment.payment_method or "Cash") == "Cash" and not payment.is_void
    if not is_cash:
        if existing and not existing.is_void:
            existing.is_void = True
            existing.void_reason = "Pembayaran Nota bukan Cash atau dibatalkan."
            existing.voided_by = user.id if user else None
            existing.voided_at = datetime.utcnow()
            audit("nota_payment", payment.id, "cash_transaction_voided", user=user)
        return existing
    reference = display_nota_number(payment.nota)
    if existing:
        existing.transaction_date = payment.payment_date
        existing.amount = payment.amount
        existing.reference_number = reference
        existing.description = payment.notes or payment.description or f"Pembayaran cash {reference}"
        existing.is_void = False
        existing.void_reason = None
        existing.voided_by = None
        existing.voided_at = None
        audit("nota_payment", payment.id, "cash_transaction_updated", new_value=str(payment.amount), user=user)
        return existing
    trx = PettyCashTransaction(
        transaction_number=generate_transaction_number(TRANSACTION_IN, payment.payment_date),
        transaction_date=payment.payment_date,
        transaction_type=TRANSACTION_IN,
        amount=payment.amount,
        source_type=SOURCE_NOTA_PAYMENT,
        source_id=payment.id,
        reference_number=reference,
        description=payment.notes or payment.description or f"Pembayaran cash {reference}",
        created_by=payment.created_by or (user.id if user else None),
    )
    db.session.add(trx)
    audit("nota_payment", payment.id, "cash_transaction_created", new_value=str(payment.amount), user=user)
    return trx


def ledger(filters=None, page=1, per_page=25):
    filters = filters or {}
    query = _filtered_query(filters)
    pagination = _latest_first_query(query).paginate(page=max(int(page or 1), 1), per_page=per_page, error_out=False)
    visible = _running_balance_map_for_page(filters, [trx.id for trx in pagination.items])
    totals = _filter_totals_from_query(query)
    return pagination, visible, totals


def running_balance_rows(transactions=None):
    transactions = transactions if transactions is not None else _ordered_query(PettyCashTransaction.query).all()
    balance = 0
    rows = []
    for trx in transactions:
        if not trx.is_void:
            balance += trx.amount if trx.transaction_type == TRANSACTION_IN else -trx.amount
        rows.append(_row(transaction=trx, running_balance=balance))
    return rows


def month_expenses(today=None):
    today = today or date.today()
    start = today.replace(day=1)
    rows = _ordered_query(
        PettyCashTransaction.query.filter(
            PettyCashTransaction.transaction_type == TRANSACTION_OUT,
            PettyCashTransaction.transaction_date >= start,
            PettyCashTransaction.transaction_date <= today,
        )
    ).all()
    active_rows = [row for row in rows if not row.is_void]
    summary = expense_summary(active_rows)
    largest = "-"
    if summary["groups"]:
        largest = max(summary["groups"].items(), key=lambda item: item[1])[0]
    return {
        "rows": rows,
        "summary": summary,
        "total": sum(row.amount for row in active_rows),
        "largest_group": largest,
        "count": len(active_rows),
    }


def build_petty_cash_pdf(filters, user):
    rows = running_balance_rows(_ordered_query(_filtered_query(filters)).all())
    active = [row.transaction for row in rows if not row.transaction.is_void]
    total_in = sum(row.amount for row in active if row.transaction_type == TRANSACTION_IN)
    total_out = sum(row.amount for row in active if row.transaction_type == TRANSACTION_OUT)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=22, bottomMargin=22)
    styles = _summary_pdf_styles()
    story = [
        Paragraph("EVPRO TEXTILE", styles["SummaryBrand"]),
        Paragraph("Laporan Kas Kecil", styles["SummaryTitle"]),
        Paragraph(f"Tanggal cetak: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Dicetak oleh: {getattr(user, 'name', '-')}", styles["SummaryMeta"]),
        Spacer(1, 12),
        _summary_metric_table(total_in, total_out, total_in - total_out, styles),
        Spacer(1, 8),
        Paragraph("Keterangan: transaksi yang dibatalkan tetap tampil dalam riwayat, tetapi tidak memengaruhi saldo berjalan.", styles["SummaryNote"]),
        Spacer(1, 12),
    ]
    table_rows = [["Tanggal", "SubKelompok", "Keterangan", "Masuk", "Keluar", "Saldo"]]
    for row in rows:
        trx = row.transaction
        table_rows.append([
            pretty_date(trx.transaction_date),
            trx.category.category_name if trx.category else INCOME_SOURCES.get(trx.source_type, trx.source_type),
            trx.description or "-",
            rupiah(trx.amount) if trx.transaction_type == TRANSACTION_IN and not trx.is_void else "-",
            rupiah(trx.amount) if trx.transaction_type == TRANSACTION_OUT and not trx.is_void else "-",
            rupiah(row.running_balance),
        ])
    story.append(
        Table(
            [[_p(cell, styles["SummaryTableHead"] if index == 0 else styles["SummaryTableText"]) for cell in row] for index, row in enumerate(table_rows)],
            repeatRows=1,
            colWidths=[68, 160, 270, 92, 92, 92],
            style=_summary_pdf_table_style(),
        )
    )
    doc.build(story)
    buffer.seek(0)
    return buffer


def build_petty_cash_detail_pdf(filters, user):
    report = petty_cash_detail_report(filters, user)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=16, rightMargin=16, topMargin=18, bottomMargin=22)
    styles = _pdf_styles()
    story = [
        Paragraph("EVPRO TEXTILE", styles["ReportBrand"]),
        Paragraph("LAPORAN DETAIL KAS KECIL", styles["ReportTitle"]),
        _meta_table(report, styles),
        Spacer(1, 8),
        _summary_table(report["summary"], styles),
        Spacer(1, 10),
        Paragraph("REKAP PENGELUARAN BERDASARKAN KELOMPOK", styles["SectionTitle"]),
        _group_recap_table(report["group_recap"], styles),
        Spacer(1, 10),
        Paragraph("RINCIAN PENGELUARAN PER SUBKATEGORI", styles["SectionTitle"]),
    ]
    for group in report["subcategory_recap"]:
        story.extend([
            Paragraph(group["group_name"], styles["GroupTitle"]),
            _subcategory_recap_table(group, styles),
            Spacer(1, 6),
        ])
    story.extend([
        Spacer(1, 4),
        Paragraph("PEMISAHAN JENIS PENGELUARAN", styles["SectionTitle"]),
        _classification_table(report["classification"], styles),
        Spacer(1, 10),
        Paragraph("REKAP PEMASUKAN BERDASARKAN SUMBER", styles["SectionTitle"]),
        _income_recap_table(report["income_recap"], styles),
        PageBreak(),
        Paragraph("DETAIL TRANSAKSI KAS KECIL", styles["SectionTitle"]),
    ])
    if report["transactions"]:
        story.append(_detail_transactions_table(report["transactions"], styles))
    else:
        story.append(Paragraph("Tidak ada transaksi pada periode dan filter yang dipilih", styles["EmptyText"]))
    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    buffer.seek(0)
    return buffer


def petty_cash_detail_report(filters, user=None):
    filters = filters or {}
    period_start, period_end = _period_bounds(filters)
    opening_balance = _opening_balance_before(period_start)
    transactions = _ordered_query(
        _filtered_query(filters).options(joinedload(PettyCashTransaction.category), joinedload(PettyCashTransaction.creator))
    ).all()
    running_rows = []
    running_balance = opening_balance
    active_count = 0
    void_count = 0
    for index, trx in enumerate(transactions, start=1):
        if trx.is_void:
            void_count += 1
        else:
            active_count += 1
            running_balance += trx.amount if trx.transaction_type == TRANSACTION_IN else -trx.amount
        running_rows.append(_row(no=index, transaction=trx, running_balance=running_balance))

    active_transactions = [row.transaction for row in running_rows if not row.transaction.is_void]
    total_income = sum(trx.amount for trx in active_transactions if trx.transaction_type == TRANSACTION_IN)
    total_expense = sum(trx.amount for trx in active_transactions if trx.transaction_type == TRANSACTION_OUT)
    net_change = total_income - total_expense
    group_recap = _detail_group_recap(filters, total_expense)
    subcategory_recap = _detail_subcategory_recap(filters)
    classification = _detail_classification(filters)
    income_recap = _detail_income_recap(filters)
    return {
        "filters": filters,
        "meta": _detail_filter_meta(filters, user),
        "summary": {
            "opening_balance": opening_balance,
            "total_income": total_income,
            "total_expense": total_expense,
            "net_change": net_change,
            "ending_balance": opening_balance + net_change,
            "active_count": active_count,
            "void_count": void_count,
        },
        "group_recap": group_recap,
        "subcategory_recap": subcategory_recap,
        "classification": classification,
        "income_recap": income_recap,
        "transactions": running_rows,
        "period_start": period_start,
        "period_end": period_end,
    }


def _detail_group_recap(filters, total_expense):
    group_filter = str(filters.get("group_name") or "").strip()
    category_filter = _parse_int(filters.get("category_id"))
    category_rows = _filtered_categories_for_detail(group_filter, category_filter)
    groups = {}
    for category in category_rows:
        row = groups.setdefault(
            category.group_name,
            {"group_name": category.group_name, "count": 0, "total": 0, "sort_order": category.sort_order},
        )
        row["sort_order"] = min(row["sort_order"], category.sort_order)
    aggregate_rows = (
        _filtered_query(filters)
        .filter(
            PettyCashTransaction.transaction_type == TRANSACTION_OUT,
            PettyCashTransaction.is_void.is_(False),
        )
        .with_entities(
            PettyCashCategory.group_name,
            func.count(PettyCashTransaction.id),
            func.coalesce(func.sum(PettyCashTransaction.amount), 0),
        )
        .group_by(PettyCashCategory.group_name)
        .all()
    )
    for group_name, count, total in aggregate_rows:
        if group_name in groups:
            groups[group_name]["count"] = int(count or 0)
            groups[group_name]["total"] = int(total or 0)
    rows = []
    for index, row in enumerate(sorted(groups.values(), key=lambda item: (item["sort_order"], item["group_name"])), start=1):
        percent = (row["total"] / total_expense * 100) if total_expense else 0
        rows.append(_row(no=index, group_name=row["group_name"], count=row["count"], total=row["total"], percent=percent))
    return rows


def _detail_subcategory_recap(filters):
    group_filter = str(filters.get("group_name") or "").strip()
    category_filter = _parse_int(filters.get("category_id"))
    category_rows = _filtered_categories_for_detail(group_filter, category_filter)
    category_lookup = {
        category.id: {
            "category": category,
            "count": 0,
            "total": 0,
        }
        for category in category_rows
    }
    aggregate_rows = (
        _filtered_query(filters)
        .filter(
            PettyCashTransaction.transaction_type == TRANSACTION_OUT,
            PettyCashTransaction.is_void.is_(False),
        )
        .with_entities(
            PettyCashTransaction.category_id,
            func.count(PettyCashTransaction.id),
            func.coalesce(func.sum(PettyCashTransaction.amount), 0),
        )
        .group_by(PettyCashTransaction.category_id)
        .all()
    )
    for category_id, count, total in aggregate_rows:
        if category_id in category_lookup:
            category_lookup[category_id]["count"] = int(count or 0)
            category_lookup[category_id]["total"] = int(total or 0)
    grouped = {}
    for item in category_lookup.values():
        category = item["category"]
        group = grouped.setdefault(
            category.group_name,
            {"group_name": category.group_name, "sort_order": category.sort_order, "rows": [], "count": 0, "total": 0},
        )
        group["sort_order"] = min(group["sort_order"], category.sort_order)
        group["rows"].append(_row(category_name=category.category_name, count=item["count"], total=item["total"], sort_order=category.sort_order))
        group["count"] += item["count"]
        group["total"] += item["total"]
    result = []
    for group in sorted(grouped.values(), key=lambda item: (item["sort_order"], item["group_name"])):
        group["rows"] = sorted(group["rows"], key=lambda item: item.sort_order)
        result.append(group)
    return result


def _detail_classification(filters):
    totals = {
        SOURCE_OPERATING_EXPENSE: 0,
        SOURCE_EMPLOYEE_CASH_ADVANCE: 0,
        SOURCE_ALLOWANCE_RESERVE: 0,
        SOURCE_TRANSFER_TO_MAIN_CASH: 0,
        SOURCE_OWNER_WITHDRAWAL: 0,
    }
    rows = (
        _filtered_query(filters)
        .filter(PettyCashTransaction.transaction_type == TRANSACTION_OUT, PettyCashTransaction.is_void.is_(False))
        .with_entities(
            PettyCashCategory.category_type,
            PettyCashCategory.is_operational_expense,
            func.coalesce(func.sum(PettyCashTransaction.amount), 0),
        )
        .group_by(PettyCashCategory.category_type, PettyCashCategory.is_operational_expense)
        .all()
    )
    for category_type, is_operational, total in rows:
        key = SOURCE_OPERATING_EXPENSE if is_operational else category_type
        if key in totals:
            totals[key] += int(total or 0)
    total_cash_out = sum(totals.values())
    return [
        _row(label="Biaya Operasional", total=totals[SOURCE_OPERATING_EXPENSE]),
        _row(label="Kasbon Karyawan", total=totals[SOURCE_EMPLOYEE_CASH_ADVANCE]),
        _row(label="Penyisihan Tunjangan", total=totals[SOURCE_ALLOWANCE_RESERVE]),
        _row(label="Transfer ke Kas Besar", total=totals[SOURCE_TRANSFER_TO_MAIN_CASH]),
        _row(label="Prive/Pengambilan Pemilik", total=totals[SOURCE_OWNER_WITHDRAWAL]),
        _row(label="Total Seluruh Pengeluaran Kas", total=total_cash_out),
    ]


def _detail_income_recap(filters):
    totals = {source_type: {"label": label, "count": 0, "total": 0} for source_type, label in INCOME_SOURCES.items()}
    rows = (
        _filtered_query(filters)
        .filter(PettyCashTransaction.transaction_type == TRANSACTION_IN, PettyCashTransaction.is_void.is_(False))
        .with_entities(
            PettyCashTransaction.source_type,
            func.count(PettyCashTransaction.id),
            func.coalesce(func.sum(PettyCashTransaction.amount), 0),
        )
        .group_by(PettyCashTransaction.source_type)
        .all()
    )
    for source_type, count, total in rows:
        row = totals.setdefault(source_type, {"label": INCOME_SOURCES.get(source_type, source_type), "count": 0, "total": 0})
        row["count"] = int(count or 0)
        row["total"] = int(total or 0)
    result = [_row(source=source_type, label=data["label"], count=data["count"], total=data["total"]) for source_type, data in totals.items()]
    result.append(_row(source="TOTAL", label="Total Seluruh Pemasukan", count=sum(row.count for row in result), total=sum(row.total for row in result)))
    return result


def _filtered_categories_for_detail(group_filter="", category_filter=0):
    query = PettyCashCategory.query.filter(PettyCashCategory.is_active.is_(True))
    if group_filter:
        query = query.filter(PettyCashCategory.group_name == group_filter)
    if category_filter:
        query = query.filter(PettyCashCategory.id == category_filter)
    return query.order_by(PettyCashCategory.sort_order.asc(), PettyCashCategory.group_name.asc(), PettyCashCategory.category_name.asc()).all()


def _period_bounds(filters):
    today = date.today()
    month = _parse_int(filters.get("month")) or today.month
    year = _parse_int(filters.get("year")) or today.year
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def _opening_balance_before(period_start):
    income = db.session.query(func.coalesce(func.sum(PettyCashTransaction.amount), 0)).filter(
        PettyCashTransaction.transaction_date < period_start,
        PettyCashTransaction.transaction_type == TRANSACTION_IN,
        PettyCashTransaction.is_void.is_(False),
    ).scalar() or 0
    expense = db.session.query(func.coalesce(func.sum(PettyCashTransaction.amount), 0)).filter(
        PettyCashTransaction.transaction_date < period_start,
        PettyCashTransaction.transaction_type == TRANSACTION_OUT,
        PettyCashTransaction.is_void.is_(False),
    ).scalar() or 0
    return int(income or 0) - int(expense or 0)


def _detail_filter_meta(filters, user):
    month = _parse_int(filters.get("month")) or date.today().month
    year = _parse_int(filters.get("year")) or date.today().year
    month_label = dict(MONTH_OPTIONS).get(month, str(month))
    category = PettyCashCategory.query.get(_parse_int(filters.get("category_id"))) if _parse_int(filters.get("category_id")) else None
    creator = User.query.get(_parse_int(filters.get("created_by"))) if _parse_int(filters.get("created_by")) else None
    return {
        "period": f"{month_label} {year}",
        "transaction_type": {"IN": "Pemasukan", "OUT": "Pengeluaran"}.get(filters.get("transaction_type"), "Semua Jenis"),
        "status": {"active": "Aktif", "void": "Dibatalkan"}.get(filters.get("status"), "Semua Status"),
        "group": filters.get("group_name") or "Semua Kelompok",
        "category": category.category_name if category else "Semua Subkategori",
        "user": creator.name if creator else "Semua User",
        "q": str(filters.get("q") or "").strip(),
        "printed_at": datetime.now().strftime("%d/%m/%Y %H:%M WIB"),
        "printed_by": getattr(user, "name", None) or getattr(user, "username", None) or "-",
    }


def _pdf_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportBrand", parent=styles["Heading2"], fontSize=10, leading=12, textColor=colors.HexColor("#c5162e"), spaceAfter=2))
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontSize=15, leading=18, textColor=colors.HexColor("#20242a"), spaceAfter=6))
    styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading3"], fontSize=9, leading=11, textColor=colors.HexColor("#20242a"), spaceBefore=2, spaceAfter=4))
    styles.add(ParagraphStyle(name="GroupTitle", parent=styles["Heading4"], fontSize=8, leading=10, textColor=colors.HexColor("#20242a"), spaceBefore=2, spaceAfter=3))
    styles.add(ParagraphStyle(name="TableText", parent=styles["BodyText"], fontSize=6.2, leading=7.4, textColor=colors.HexColor("#20242a")))
    styles.add(ParagraphStyle(name="TableTextSmall", parent=styles["TableText"], fontSize=5.4, leading=6.5))
    styles.add(ParagraphStyle(name="TableHead", parent=styles["TableText"], fontName="Helvetica-Bold", textColor=colors.white))
    styles.add(ParagraphStyle(name="MetaText", parent=styles["BodyText"], fontSize=7, leading=8.5, textColor=colors.HexColor("#20242a")))
    styles.add(ParagraphStyle(name="EmptyText", parent=styles["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#687182")))
    return styles


def _meta_table(report, styles):
    meta = report["meta"]
    rows = [
        ["Periode", meta["period"], "Jenis", meta["transaction_type"], "Status", meta["status"]],
        ["Kelompok", meta["group"], "Subkategori", meta["category"], "User", meta["user"]],
        ["Dicetak", meta["printed_at"], "Dicetak oleh", meta["printed_by"], "Cari", meta["q"] or "-"],
    ]
    return Table(
        [[_p(cell, styles["MetaText"]) for cell in row] for row in rows],
        colWidths=[48, 142, 58, 130, 58, 130],
        style=_detail_table_style(header=False, compact=True),
    )


def _summary_table(summary, styles):
    rows = [
        ["Saldo Awal Periode", rupiah(summary["opening_balance"]), "Total Pemasukan", rupiah(summary["total_income"]), "Total Pengeluaran", rupiah(summary["total_expense"])],
        ["Perubahan Kas Bersih", rupiah(summary["net_change"]), "Saldo Akhir", rupiah(summary["ending_balance"]), "Transaksi Aktif/Batal", f'{summary["active_count"]} / {summary["void_count"]}'],
    ]
    return Table(
        [[_p(cell, styles["MetaText"]) for cell in row] for row in rows],
        colWidths=[98, 90, 98, 90, 98, 90],
        style=_detail_table_style(header=False),
    )


def _group_recap_table(rows, styles):
    table_rows = [["No", "Kelompok Pengeluaran", "Jumlah Transaksi", "Total Pengeluaran", "Persentase"]]
    total_count = 0
    total_amount = 0
    for row in rows:
        total_count += row.count
        total_amount += row.total
        table_rows.append([row.no, row.group_name, row.count, rupiah(row.total), f"{row.percent:.2f}%"])
    table_rows.append(["", "TOTAL SELURUH PENGELUARAN", total_count, rupiah(total_amount), "100.00%" if total_amount else "0.00%"])
    return Table(
        [[_p(cell, styles["TableHead"] if index == 0 else styles["TableText"]) for cell in row] for index, row in enumerate(table_rows)],
        repeatRows=1,
        colWidths=[26, 260, 82, 100, 72],
        style=_detail_table_style(),
    )


def _subcategory_recap_table(group, styles):
    rows = [["Subkategori", "Jumlah Transaksi", "Total Pengeluaran"]]
    for row in group["rows"]:
        rows.append([row.category_name, row.count, rupiah(row.total)])
    rows.append(["Total Kelompok", group["count"], rupiah(group["total"])])
    return Table(
        [[_p(cell, styles["TableHead"] if index == 0 else styles["TableText"]) for cell in row] for index, row in enumerate(rows)],
        repeatRows=1,
        colWidths=[300, 100, 120],
        style=_detail_table_style(),
    )


def _classification_table(rows, styles):
    table_rows = [["Klasifikasi", "Total"]]
    table_rows.extend([[row.label, rupiah(row.total)] for row in rows])
    return Table(
        [[_p(cell, styles["TableHead"] if index == 0 else styles["TableText"]) for cell in row] for index, row in enumerate(table_rows)],
        repeatRows=1,
        colWidths=[300, 140],
        style=_detail_table_style(),
    )


def _income_recap_table(rows, styles):
    table_rows = [["Sumber Pemasukan", "Jumlah Transaksi", "Total"]]
    table_rows.extend([[row.label, row.count, rupiah(row.total)] for row in rows])
    return Table(
        [[_p(cell, styles["TableHead"] if index == 0 else styles["TableText"]) for cell in row] for index, row in enumerate(table_rows)],
        repeatRows=1,
        colWidths=[300, 100, 120],
        style=_detail_table_style(),
    )


def _detail_transactions_table(rows, styles):
    table_rows = [[
        "No", "Tanggal", "Nomor Transaksi", "Jenis", "Kelompok", "Subkategori",
        "Keterangan", "Pemasukan", "Pengeluaran", "Saldo Berjalan", "Dicatat Oleh", "Status",
    ]]
    for row in rows:
        trx = row.transaction
        table_rows.append([
            row.no,
            pretty_date(trx.transaction_date),
            trx.transaction_number,
            "Masuk" if trx.transaction_type == TRANSACTION_IN else "Keluar",
            trx.category.group_name if trx.category else INCOME_SOURCES.get(trx.source_type, trx.source_type),
            trx.category.category_name if trx.category else "-",
            trx.description or "-",
            rupiah(trx.amount) if trx.transaction_type == TRANSACTION_IN and not trx.is_void else "-",
            rupiah(trx.amount) if trx.transaction_type == TRANSACTION_OUT and not trx.is_void else "-",
            rupiah(row.running_balance),
            trx.creator.name if trx.creator else "-",
            "Dibatalkan" if trx.is_void else "Aktif",
        ])
    return Table(
        [[_p(cell, styles["TableHead"] if index == 0 else styles["TableTextSmall"]) for cell in row] for index, row in enumerate(table_rows)],
        repeatRows=1,
        colWidths=[20, 44, 82, 38, 88, 84, 136, 62, 62, 72, 58, 46],
        style=_detail_table_style(),
    )


def _detail_table_style(header=True, compact=False):
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c8ced6")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2 if compact else 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 if compact else 3),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c5162e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ])
    return TableStyle(commands)


def _p(value, style):
    text = str(value if value is not None else "-")
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
    return Paragraph(text, style)


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#687182"))
    canvas.drawRightString(820, 12, f"Halaman {doc.page}")
    canvas.restoreState()


def _summary_pdf_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SummaryBrand", parent=styles["Heading2"], fontSize=12, leading=14, textColor=colors.HexColor("#c5162e"), spaceAfter=2))
    styles.add(ParagraphStyle(name="SummaryTitle", parent=styles["Title"], fontSize=18, leading=22, textColor=colors.HexColor("#20242a"), spaceAfter=4))
    styles.add(ParagraphStyle(name="SummaryMeta", parent=styles["BodyText"], fontSize=9.5, leading=12, textColor=colors.HexColor("#555f6f")))
    styles.add(ParagraphStyle(name="SummaryNote", parent=styles["BodyText"], fontSize=9, leading=11, textColor=colors.HexColor("#555f6f")))
    styles.add(ParagraphStyle(name="SummaryMetricLabel", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=colors.white))
    styles.add(ParagraphStyle(name="SummaryMetricValue", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=colors.white))
    styles.add(ParagraphStyle(name="SummaryTableHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=colors.white))
    styles.add(ParagraphStyle(name="SummaryTableText", parent=styles["BodyText"], fontSize=8.5, leading=10.5, textColor=colors.HexColor("#20242a")))
    return styles


def _summary_metric_table(total_in, total_out, ending_balance, styles):
    rows = [
        [
            _summary_metric_cell("Total Pemasukan", rupiah(total_in), styles),
            _summary_metric_cell("Total Pengeluaran", rupiah(total_out), styles),
            _summary_metric_cell("Saldo Akhir", rupiah(ending_balance), styles),
        ]
    ]
    table = Table(rows, colWidths=[250, 250, 250], rowHeights=[54])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#c5162e")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#991226")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f3b3bf")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _summary_metric_cell(label, value, styles):
    return [Paragraph(label, styles["SummaryMetricLabel"]), Paragraph(value, styles["SummaryMetricValue"])]


def _summary_pdf_table_style():
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c5162e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c8ced6")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f8fa")]),
        ]
    )


def generate_transaction_number(transaction_type, transaction_date=None):
    transaction_date = transaction_date or date.today()
    prefix = f"KK-{transaction_type}-{transaction_date.strftime('%Y%m')}-"
    existing = PettyCashTransaction.query.filter(PettyCashTransaction.transaction_number.like(f"{prefix}%")).with_entities(PettyCashTransaction.transaction_number).all()
    sequences = []
    for number, in existing:
        suffix = str(number or "").replace(prefix, "")
        if suffix.isdigit():
            sequences.append(int(suffix))
    return f"{prefix}{(max(sequences) if sequences else 0) + 1:04d}"


def audit(entity_type, entity_id, action, old_value=None, new_value=None, notes=None, user=None):
    db.session.add(FinancialAuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        notes=notes,
        created_by=user.id if user else None,
    ))


def _filtered_query(filters):
    query = PettyCashTransaction.query.outerjoin(PettyCashCategory)
    month = _parse_int(filters.get("month"))
    year = _parse_int(filters.get("year"))
    if year:
        query = query.filter(func.strftime("%Y", PettyCashTransaction.transaction_date) == str(year))
    if month:
        query = query.filter(func.strftime("%m", PettyCashTransaction.transaction_date) == f"{month:02d}")
    if filters.get("transaction_type"):
        query = query.filter(PettyCashTransaction.transaction_type == filters["transaction_type"])
    if filters.get("category_id"):
        query = query.filter(PettyCashTransaction.category_id == _parse_int(filters.get("category_id")))
    if filters.get("group_name"):
        query = query.filter(PettyCashCategory.group_name == filters["group_name"])
    if filters.get("created_by"):
        query = query.filter(PettyCashTransaction.created_by == _parse_int(filters.get("created_by")))
    if filters.get("status") == "active":
        query = query.filter(PettyCashTransaction.is_void.is_(False))
    if filters.get("status") == "void":
        query = query.filter(PettyCashTransaction.is_void.is_(True))
    q = str(filters.get("q") or "").strip()
    if q:
        needle = f"%{q}%"
        query = query.filter(or_(PettyCashTransaction.reference_number.ilike(needle), PettyCashTransaction.description.ilike(needle), PettyCashTransaction.transaction_number.ilike(needle)))
    return query


def _ordered_query(query):
    return query.order_by(PettyCashTransaction.transaction_date.asc(), PettyCashTransaction.created_at.asc(), PettyCashTransaction.id.asc())


def _latest_first_query(query):
    return query.order_by(PettyCashTransaction.transaction_date.desc(), PettyCashTransaction.created_at.desc(), PettyCashTransaction.id.desc())


def _running_balance_map_for_page(filters, transaction_ids):
    if not transaction_ids:
        return {}
    signed_amount = case(
        (
            PettyCashTransaction.is_void.is_(False),
            case(
                (PettyCashTransaction.transaction_type == TRANSACTION_IN, PettyCashTransaction.amount),
                else_=-PettyCashTransaction.amount,
            ),
        ),
        else_=0,
    )
    running_subquery = (
        _filtered_query(filters)
        .with_entities(
            PettyCashTransaction.id.label("transaction_id"),
            func.sum(signed_amount)
            .over(
                order_by=(
                    PettyCashTransaction.transaction_date.asc(),
                    PettyCashTransaction.created_at.asc(),
                    PettyCashTransaction.id.asc(),
                )
            )
            .label("running_balance"),
        )
        .subquery()
    )
    rows = (
        db.session.query(running_subquery.c.transaction_id, running_subquery.c.running_balance)
        .filter(running_subquery.c.transaction_id.in_(transaction_ids))
        .all()
    )
    return {row.transaction_id: _row(running_balance=row.running_balance or 0) for row in rows}


def _active_query():
    return PettyCashTransaction.query.filter(PettyCashTransaction.is_void.is_(False))


def _sum_transactions(transaction_type):
    return db.session.query(func.coalesce(func.sum(PettyCashTransaction.amount), 0)).filter(
        PettyCashTransaction.transaction_type == transaction_type,
        PettyCashTransaction.is_void.is_(False),
    ).scalar() or 0


def _filter_totals(transactions):
    active = [row for row in transactions if not row.is_void]
    return {
        "income": sum(row.amount for row in active if row.transaction_type == TRANSACTION_IN),
        "expense": sum(row.amount for row in active if row.transaction_type == TRANSACTION_OUT),
        "net": sum(row.amount if row.transaction_type == TRANSACTION_IN else -row.amount for row in active),
        "count": len(active),
    }


def _filter_totals_from_query(query):
    income_amount = case(
        (
            PettyCashTransaction.is_void.is_(False) & (PettyCashTransaction.transaction_type == TRANSACTION_IN),
            PettyCashTransaction.amount,
        ),
        else_=0,
    )
    expense_amount = case(
        (
            PettyCashTransaction.is_void.is_(False) & (PettyCashTransaction.transaction_type == TRANSACTION_OUT),
            PettyCashTransaction.amount,
        ),
        else_=0,
    )
    active_count = case((PettyCashTransaction.is_void.is_(False), 1), else_=0)
    income, expense, count = query.with_entities(
        func.coalesce(func.sum(income_amount), 0),
        func.coalesce(func.sum(expense_amount), 0),
        func.coalesce(func.sum(active_count), 0),
    ).one()
    return {
        "income": income,
        "expense": expense,
        "net": income - expense,
        "count": count,
    }


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


def _parse_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _save_attachment(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    filename = file_storage.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    allowed = filename.lower().endswith((".jpg", ".jpeg", ".png", ".pdf"))
    if not allowed:
        raise ValueError("Bukti transaksi harus berupa JPG, PNG, atau PDF.")
    from flask import current_app
    from pathlib import Path
    from uuid import uuid4

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"]) / "petty_cash"
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}_{filename}"
    file_storage.save(upload_dir / stored_name)
    return f"uploads/petty_cash/{stored_name}"


def _table_style(header=True):
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c8ced6")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if header:
        commands.extend([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c5162e")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)])
    return TableStyle(commands)


def _row(**kwargs):
    return SimpleNamespace(**kwargs)
