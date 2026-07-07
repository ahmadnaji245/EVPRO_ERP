from pathlib import Path

from flask import current_app

from utils.constants import UPLOAD_SUBFOLDERS


def ensure_upload_folders():
    upload_root = Path(current_app.config["UPLOAD_FOLDER"])
    for folder in UPLOAD_SUBFOLDERS:
        (upload_root / folder).mkdir(parents=True, exist_ok=True)


def active_class(endpoint_prefix):
    from flask import request

    return "active" if request.endpoint and request.endpoint.startswith(endpoint_prefix) else ""


def _filename_token(value, fallback, separator):
    token = []
    for char in str(value or fallback):
        if char.isalnum() or char in ("-", "_"):
            token.append(char)
        elif char.isspace() or char in ('\\', "/", ":", "*", "?", '"', "<", ">", "|"):
            token.append(separator)
        else:
            token.append(separator)
    return separator.join(part for part in "".join(token).split(separator) if part) or fallback


def sales_order_pdf_download_name(order):
    so_number = _filename_token(order.so_number, "surat-order", "-")
    if not so_number.upper().startswith("SO-"):
        so_number = f"SO-{so_number}"
    team_name = _filename_token(order.team_name, "tim", "_")
    return f"{so_number}_{team_name}.pdf"
