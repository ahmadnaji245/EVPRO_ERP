from datetime import date, datetime


def pretty_date(value):
    if not value:
        return "-"
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value)


def pretty_datetime(value):
    if not value:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value)


def number(value, digits=0):
    try:
        return f"{float(value):,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    except (TypeError, ValueError):
        return "0"


def rupiah(value):
    try:
        amount = int(value or 0)
    except (TypeError, ValueError):
        amount = 0
    return f"Rp{amount:,.0f}".replace(",", ".")


def register_filters(app):
    app.jinja_env.filters["pretty_date"] = pretty_date
    app.jinja_env.filters["pretty_datetime"] = pretty_datetime
    app.jinja_env.filters["number"] = number
    app.jinja_env.filters["rupiah"] = rupiah
