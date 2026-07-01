# ERP Architecture

## Prinsip Arsitektur

EVPRO ERP memakai arsitektur modular berbasis Flask. Setiap modul memiliki route, model, service, template, dan static asset yang dipisahkan sesuai domainnya.

Prinsip utama:

- Sales Order adalah Core Business Object.
- Modul lain harus dapat diarahkan kembali ke Sales Order.
- Business logic ditempatkan di service layer, bukan langsung di template.
- Route bertanggung jawab pada HTTP flow, validasi akses, flash message, dan pemilihan template.
- Model menggunakan SQLAlchemy.

## Core Business Object

Sales Order adalah pusat relasi ERP. Semua proses operasional dimulai dari Sales Order atau pada akhirnya harus dapat ditautkan ke Sales Order.

Contoh arah relasi:

```text
Customer Request
    -> Sales Order
        -> Approval
        -> Production
        -> Nota / Invoice
        -> Payment
        -> Repeat Order / CRM
```

## Repository Reference

| Repository | Peran |
| --- | --- |
| `ERP_SO` | Stable Source Project untuk modul Sales Order. |
| `Nota` | Stable Source Project untuk modul Nota lama. |
| `EVPRO_ERP` / `ERP` | Active Development Repository untuk integrasi ERP modular. |

Repository `ERP_SO` dan `Nota` dipakai sebagai referensi stabil. Pengembangan aktif dilakukan di repository ERP.

## Struktur Modular Saat Ini

```text
app.py
config.py
database/
models/
routes/
services/
templates/
static/
utils/
docs/
```

## Modul Aktif

| Modul | Komponen |
| --- | --- |
| Authentication | `auth_bp`, Flask-Login, model `User`. |
| Dashboard | `dashboard_bp`, template dashboard. |
| Sales Order | `sales_orders_bp`, model SO, service SO, template `so/`. |
| Nota | `nota_bp`, model Nota, service Nota, template `nota/`. |
| Tracking | `tracking_bp`, foundation untuk akses customer berbasis token. |

## Boundary Antar Modul

Mulai ERP v0.4, Sales Order dan Nota terintegrasi aktif melalui `nota.so_id`. Sales Order tetap menjadi pusat proses bisnis, sedangkan Nota menjadi dokumen turunan yang dapat dibuat dari detail Sales Order.

Aturan integrasi:

- `sales_orders.id` menjadi referensi utama.
- `notas.so_id` nullable agar Nota manual tetap didukung.
- Satu Sales Order hanya boleh memiliki satu Nota.
- Route dan UI Nota tetap admin-only.
- Output print/PDF Sales Order dan Nota tidak berubah pada v0.4.
