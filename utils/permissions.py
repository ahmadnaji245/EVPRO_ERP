from functools import wraps

from flask import abort
from flask_login import current_user, login_required

from utils.constants import normalize_user_role


ROLE_ADMIN = "admin"
ROLE_DESAIN = "desain"
ROLE_PRODUKSI = "produksi"


PERMISSIONS = {
    "dashboard.view": {ROLE_ADMIN},
    "sales_order.view": {ROLE_ADMIN, ROLE_DESAIN, ROLE_PRODUKSI},
    "sales_order.manage": {ROLE_ADMIN},
    "sales_order.pdf": {ROLE_ADMIN},
    "sales_order.setting_checklist": {ROLE_ADMIN, ROLE_DESAIN, ROLE_PRODUKSI},
    "sales_order.production_checklist": {ROLE_ADMIN, ROLE_PRODUKSI},
    "production.view": {ROLE_ADMIN, ROLE_PRODUKSI},
    "production.manage": {ROLE_ADMIN, ROLE_PRODUKSI},
    "handover.view": {ROLE_ADMIN, ROLE_DESAIN, ROLE_PRODUKSI},
    "handover.manage": {ROLE_ADMIN},
    "nota.view": {ROLE_ADMIN},
    "nota.manage": {ROLE_ADMIN},
    "master.view": {ROLE_ADMIN},
    "reports.view": {ROLE_ADMIN},
    "settings.view": {ROLE_ADMIN},
    "users.manage": {ROLE_ADMIN},
}


def current_role():
    return normalize_user_role(getattr(current_user, "role", ""))


def has_role(*roles):
    return current_user.is_authenticated and current_role() in set(roles)


def has_permission(permission):
    if not current_user.is_authenticated:
        return False
    if current_role() == ROLE_ADMIN:
        return True
    return current_role() in PERMISSIONS.get(permission, set())


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if not has_role(*roles):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def permission_required(permission):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if not has_permission(permission):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
