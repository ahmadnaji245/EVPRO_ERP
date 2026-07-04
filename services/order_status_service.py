def is_order_taken(order):
    return bool(getattr(order, "tanggal_pengambilan", None))


def get_taken_info(order):
    if not is_order_taken(order):
        return {
            "is_taken": False,
            "status": None,
            "short_status": None,
            "list_status": None,
            "badge_class": None,
            "picked_by": None,
            "pickup_date": None,
        }

    picked_by = str(getattr(order, "diambil_oleh", "") or "").strip()
    status = f"Barang sudah diambil oleh {picked_by}" if picked_by else "Barang sudah diambil"
    short_status = f"Diambil oleh {picked_by}" if picked_by else "Sudah Diambil"
    return {
        "is_taken": True,
        "status": status,
        "short_status": short_status,
        "list_status": "Diambil",
        "badge_class": "so-status-badge-taken",
        "picked_by": picked_by or None,
        "pickup_date": order.tanggal_pengambilan,
    }


def get_display_status(order):
    taken_info = get_taken_info(order)
    if taken_info["is_taken"]:
        return taken_info

    production_status = order.production_status_label
    return {
        "is_taken": False,
        "status": production_status,
        "short_status": production_status,
        "list_status": production_status,
        "badge_class": get_status_badge_class(production_status),
        "picked_by": None,
        "pickup_date": None,
    }


def get_status_badge_class(status):
    classes = {
        "Approval Customer": "so-status-badge-approval",
        "Setting": "so-status-badge-setting",
        "Printing": "so-status-badge-printing",
        "Jahit": "so-status-badge-jahit",
        "QC": "so-status-badge-qc",
        "Packing": "so-status-badge-packing",
        "Finish": "so-status-badge-finish",
        "Diambil": "so-status-badge-taken",
    }
    return classes.get(status, "text-bg-light border")
