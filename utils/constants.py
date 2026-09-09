import re


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
USER_ROLES = ["admin", "desain", "produksi", "finance"]
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
    "Finance": "finance",
    "finance": "finance",
    "Keuangan": "finance",
    "keuangan": "finance",
}

UPLOAD_SUBFOLDERS = ["brands", "designs", "customers", "pdf", "temp", "petty_cash"]

SIZE_ORDER = {
    "KXXS": 1,
    "KXS": 2,
    "KS": 3,
    "KM": 4,
    "KL": 5,
    "KXL": 6,
    "KXXL": 7,
    "WS": 10,
    "WM": 11,
    "WL": 12,
    "WXL": 13,
    "WXXL": 14,
    "W3XL": 15,
    "W4XL": 16,
    "W5XL": 17,
    "XS": 20,
    "S": 21,
    "M": 22,
    "L": 23,
    "XL": 24,
    "XXL": 25,
    "3XL": 26,
    "4XL": 27,
    "5XL": 28,
    "6XL": 29,
}
PANTS_BASE_SIZES = ("XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL")
PANTS_SIZE_SORT = SIZE_ORDER
PANTS_SIZE_PATTERN = re.compile(
    r"\bcelana\b\s*(?:=|:)?\s*(5XL|4XL|3XL|XXL|XXS|XL|XS|S|M|L)(?:\s+(kids|women))?\b",
    re.IGNORECASE,
)

SIZE_ALIASES = {
    "XXS KIDS": "KXXS",
    "XS KIDS": "KXS",
    "S KIDS": "KS",
    "M KIDS": "KM",
    "L KIDS": "KL",
    "XL KIDS": "KXL",
    "XXL KIDS": "KXXL",
    "S WOMEN": "WS",
    "M WOMEN": "WM",
    "L WOMEN": "WL",
    "XL WOMEN": "WXL",
    "XS WOMEN": "WS",
    "XXL WOMEN": "WXXL",
    "3XL WOMEN": "W3XL",
    "4XL WOMEN": "W4XL",
    "5XL WOMEN": "W5XL",
}

SIZE_GROUPS = {
    "Kids": {"KXXS", "KXS", "KS", "KM", "KL", "KXL", "KXXL"},
    "Women": {"WS", "WM", "WL", "WXL", "WXXL", "W3XL", "W4XL", "W5XL"},
}
LONG_SLEEVE_MARKERS = ("LENGAN PANJANG", "LONG SLEEVE", "LP")
LONG_SLEEVE_THREE_QUARTER_MARKERS = ("3/4", "3 / 4", "¾")
LONG_SLEEVE_SEVEN_EIGHTH_MARKERS = ("7/8", "7 / 8", "⅞")


def normalize_production_status(status):
    return LEGACY_PRODUCTION_STATUS_MAP.get(status, status if status in PRODUCTION_STATUSES else PRODUCTION_STATUSES[0])


def normalize_user_role(role):
    role = str(role or "").strip()
    return USER_ROLE_ALIASES.get(role, role.lower())


def normalize_size_key(size):
    value = " ".join(str(size or "").strip().upper().split())
    if not value:
        return ""
    value = value.replace("(", " ").replace(")", " ")
    value = " ".join(value.split())
    for marker in LONG_SLEEVE_MARKERS:
        value = value.replace(marker, " ")
    for marker in LONG_SLEEVE_THREE_QUARTER_MARKERS:
        value = value.replace(marker, " ")
    for marker in LONG_SLEEVE_SEVEN_EIGHTH_MARKERS:
        value = value.replace(marker, " ")
    value = " ".join(value.replace("-", " ").replace("_", " ").split())
    return SIZE_ALIASES.get(value, value)


def extract_pants_size_from_note(note):
    match = PANTS_SIZE_PATTERN.search(str(note or ""))
    if not match:
        return None
    return _canonical_pants_size(match.group(1), match.group(2))


def _canonical_pants_size(base_size, group=None):
    base = str(base_size or "").strip().upper()
    if base not in PANTS_BASE_SIZES:
        return None
    group_label = str(group or "").strip().title()
    size = f"{base} {group_label}" if group_label in ("Kids", "Women") else base
    return size if normalize_size_key(size) in SIZE_ORDER else None


def pants_size_from_player_size(size):
    base_size = long_sleeve_size_label(size) or " ".join(str(size or "").split())
    normalized = normalize_size_key(base_size)
    return base_size if normalized in SIZE_ORDER else None


def sort_pants_size_rows(rows):
    return sorted(
        list(rows or []),
        key=lambda row: PANTS_SIZE_SORT.get(
            normalize_size_key(row.get("size") if isinstance(row, dict) else getattr(row, "size", "")),
            10_000,
        ),
    )


def has_long_sleeve_marker(*values):
    combined = " ".join(str(value or "").upper() for value in values)
    return any(marker in combined for marker in LONG_SLEEVE_MARKERS)


def long_sleeve_type_label(*values):
    combined = " ".join(str(value or "").upper().replace("¾", "3/4").replace("⅞", "7/8") for value in values)
    if not any(marker in combined for marker in LONG_SLEEVE_MARKERS):
        return ""
    if any(marker in combined for marker in LONG_SLEEVE_THREE_QUARTER_MARKERS):
        return "Lengan Panjang 3/4"
    if any(marker in combined for marker in LONG_SLEEVE_SEVEN_EIGHTH_MARKERS):
        return "Lengan Panjang 7/8"
    return "Lengan Panjang"


def long_sleeve_size_label(size):
    value = " ".join(str(size or "").strip().replace("¾", "3/4").replace("⅞", "7/8").split())
    if not value:
        return ""
    cleaned = value
    for marker in LONG_SLEEVE_MARKERS:
        cleaned = cleaned.replace(marker.title(), " ")
        cleaned = cleaned.replace(marker, " ")
        cleaned = cleaned.replace(marker.lower(), " ")
    for marker in LONG_SLEEVE_THREE_QUARTER_MARKERS:
        cleaned = cleaned.replace(marker, " ")
    for marker in LONG_SLEEVE_SEVEN_EIGHTH_MARKERS:
        cleaned = cleaned.replace(marker, " ")
    cleaned = cleaned.replace("(", " ").replace(")", " ")
    return " ".join(cleaned.split())


def long_sleeve_sort_rank(sleeve_type):
    return {
        "Lengan Panjang": 0,
        "Lengan Panjang 3/4": 1,
        "Lengan Panjang 7/8": 2,
    }.get(sleeve_type, 99)


def size_sort_rank(size):
    return SIZE_ORDER.get(normalize_size_key(size), 10_000)


def size_group_name(size):
    key = normalize_size_key(size)
    for group_name, group_sizes in SIZE_GROUPS.items():
        if key in group_sizes:
            return group_name
    return "Reguler"


def sort_players_by_size(players):
    return sorted(
        list(players or []),
        key=lambda item: (
            size_sort_rank(getattr(item, "size", "")),
            getattr(item, "sort_order", 0) or 0,
            getattr(item, "id", 0) or 0,
        ),
    )


def sort_size_rows(rows):
    return sorted(
        list(rows or []),
        key=lambda row: (
            size_sort_rank(row.get("size") if isinstance(row, dict) else getattr(row, "size", "")),
            row.get("_first_index", 0) if isinstance(row, dict) else getattr(row, "_first_index", 0),
        ),
    )


def sort_long_sleeve_rows(rows):
    return sorted(
        list(rows or []),
        key=lambda row: (
            long_sleeve_sort_rank(row.get("sleeve_type") if isinstance(row, dict) else getattr(row, "sleeve_type", "")),
            size_sort_rank(row.get("base_size") if isinstance(row, dict) else getattr(row, "base_size", "")),
            row.get("_first_index", 0) if isinstance(row, dict) else getattr(row, "_first_index", 0),
        ),
    )


def user_has_role(user, role):
    return normalize_user_role(getattr(user, "role", "")) == role


def user_is_admin(user):
    return user_has_role(user, "admin")


def user_is_desain(user):
    return user_has_role(user, "desain")


def user_is_produksi(user):
    return user_has_role(user, "produksi")
