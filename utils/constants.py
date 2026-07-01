APP_NAME = "EVPRO TEXTILE ERP"
APP_TAGLINE = "Sales Order Management System"

APPROVAL_STATUSES = ["pending", "approved", "cancelled"]
CUSTOMER_PORTAL_STATUSES = [
    "Draft",
    "Menunggu Persetujuan Desain",
    "Revisi Customer",
    "Desain Disetujui",
    "Produksi",
    "Selesai",
]
PRODUCTION_STATUSES = ["Desain", "Setting", "Printing", "Jahit", "QC", "Packing", "Selesai"]
LEGACY_PRODUCTION_STATUS_MAP = {
    "Menunggu Setting": "Setting",
    "Menunggu QC": "QC",
    "Menunggu Finish": "Packing",
    "Finish": "Selesai",
}
USER_ROLES = ["admin", "produksi"]
USER_ROLE_ALIASES = {
    "Admin": "admin",
    "Produksi": "produksi",
    "production": "produksi",
    "Production": "produksi",
    "Desainer": "produksi",
    "designer": "produksi",
    "Designer": "produksi",
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


def user_is_produksi(user):
    return user_has_role(user, "produksi")
