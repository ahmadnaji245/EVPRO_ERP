# Coding Standard

## Prinsip Umum

- Gunakan pola modular.
- Gunakan Flask Blueprint untuk setiap modul.
- Gunakan SQLAlchemy untuk database.
- Gunakan service layer untuk business logic.
- Gunakan helper/utility untuk logic umum.
- Jangan duplicate code.
- Jangan menaruh business logic berat di template.

## Struktur Modul

Setiap modul idealnya memiliki:

```text
routes/<module>_routes.py
models/<module>.py
services/<module>_service.py
templates/<module>/
static/js/<module>_*.js
```

## Blueprint

Setiap modul harus memakai Blueprint.

Contoh konsep:

```python
module_bp = Blueprint("module", __name__, url_prefix="/module")
```

## SQLAlchemy

Semua model baru harus memakai SQLAlchemy. Jangan menambahkan database layer sqlite3 manual.

## Services

Service layer digunakan untuk:

- Query data.
- Create/update/delete.
- Validasi domain.
- Kalkulasi total.
- Sinkronisasi child records.

## Route

Route digunakan untuk:

- HTTP method handling.
- Authentication.
- Authorization.
- Flash message.
- Redirect.
- Render template.

Semua route harus menggunakan decorator sesuai role:

- `@login_required` untuk route internal.
- Guard admin untuk route admin-only.
- Secure token validation untuk customer-facing route.

## Template

Template harus fokus pada presentasi data. Hindari query database langsung dari template.

## Static JS

JavaScript khusus modul harus dipisahkan jika hanya dipakai oleh modul tertentu.

Contoh:

- `static/js/nota_form.js`
- `static/js/sales_order_create.js`
- `static/js/sales_order_edit.js`

## Naming

- Class model memakai PascalCase.
- Function dan variable memakai snake_case.
- Blueprint endpoint harus stabil agar template tidak mudah rusak.

## Release Discipline

- Fitur Planned tidak boleh didokumentasikan sebagai Active.
- Integrasi lintas modul harus mengikuti roadmap.
- Source project lama hanya dipakai sebagai referensi.
