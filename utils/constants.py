APP_NAME = "EVPRO TEXTILE ERP"
APP_TAGLINE = "Surat Order Management System"

APPROVAL_STATUSES = ["pending", "approved", "cancelled"]
CUSTOMER_PORTAL_STATUSES = [
    "Approval Customer",
    "Setting",
    "Printing",
    "Jahit",
    "QC",
    "Packing",
    "Finish",
]
PRODUCTION_VENDORS = ["Mas Amar", "Mas Syukron"]
PRODUCTION_STATUSES = [
    "Approval Customer",
    "Setting",
    "Printing",
    "Jahit",
    "QC",
    "Packing",
    "Finish",
]
LEGACY_PRODUCTION_STATUS_MAP = {
    "Desain": "Approval Customer",
    "Menunggu Persetujuan Desain": "Approval Customer",
    "Revisi Customer": "Approval Customer",
    "Desain Disetujui": "Setting",
    "Produksi": "Jahit",
    "Menunggu Assign": "Approval Customer",
    "Dikirim ke Vendor": "Jahit",
    "Sedang Diproduksi": "Printing",
    "Potong": "Printing",
    "Finishing": "Packing",
    "Barang Masuk": "QC",
    "Menunggu Setting": "Setting",
    "Menunggu QC": "QC",
    "Menunggu Finish": "Packing",
    "Selesai": "Finish",
    "Terkirim dari Vendor": "QC",
}
USER_ROLES = ["admin", "desain", "produksi"]
USER_ROLE_ALIASES = {
    "Admin": "admin",
    "Desain": "desain",
    "Designer": "desain",
    "designer": "desain",
    "Desainer": "desain",
    "desainer": "desain",
    "Produksi": "produksi",
    "production": "produksi",
    "Production": "produksi",
    "QC": "produksi",
    "qc": "produksi",
}

UPLOAD_SUBFOLDERS = ["brands", "designs", "customers", "pdf", "temp"]


def normalize_production_status(status):
    return LEGACY_PRODUCTION_STATUS_MAP.get(status, status if status in PRODUCTION_STATUSES else PRODUCTION_STATUSES[0])


def normalize_user_role(role):
    role = str(role or "").strip()
    return USER_ROLE_ALIASES.get(role, role.lower())


def user_has_role(user, role):
    return normalize_user_role(getattr(user, "role", "")) == role


def user_is_admin(user):
    return user_has_role(user, "admin")


def user_is_desain(user):
    return user_has_role(user, "desain")


def user_is_produksi(user):
    return user_has_role(user, "produksi")
