# User Roles

## Prinsip Akses

Setiap route harus memiliki authentication dan authorization sesuai kebutuhan modul. Saat ini sistem memakai Flask-Login dengan role dasar.

## Role

### Owner

Status: Planned.

Hak akses target:

- Semua modul.
- Laporan bisnis.
- Finance.
- User management.
- AI insight.

### Admin

Status: Active.

Hak akses:

- Dashboard internal.
- Sales Order.
- Create/edit/delete Sales Order.
- Approval admin.
- Nota.
- Create/edit Nota.
- Tambah pembayaran.
- Ubah status Nota.

Admin boleh membuka modul Nota.

### Produksi

Status: Active.

Hak akses:

- Sales Order.
- Dashboard dasar.
- Update production status/checklist sesuai kebutuhan operasional.

Batasan:

- Produksi tidak boleh membuka route Nota.
- Produksi tidak boleh create/edit/delete Sales Order admin-only.

### Customer

Status: Planned untuk portal penuh.

Konsep akses:

- Customer tidak memiliki login dashboard ERP.
- Customer membuka halaman approval menggunakan secure token.
- Customer hanya dapat melihat informasi yang aman untuk eksternal.

Customer hanya boleh membuka approval page menggunakan secure token.

## Matriks Akses

| Modul / Aksi | Owner | Admin | Produksi | Customer |
| --- | --- | --- | --- | --- |
| Dashboard internal | Planned | Yes | Limited | No |
| Sales Order list/detail | Planned | Yes | Yes | No |
| Create/edit Sales Order | Planned | Yes | No | No |
| Nota | Planned | Yes | No | No |
| Production checklist | Planned | Yes | Yes | No |
| Customer approval page | Planned | Limited | No | Token only |
| Role management | Planned | Planned | No | No |
