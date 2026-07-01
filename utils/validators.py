def required(value):
    return bool(str(value or "").strip())


def normalize_code(value):
    return str(value or "").strip().upper()
