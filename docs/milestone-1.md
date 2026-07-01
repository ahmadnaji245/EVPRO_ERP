# Milestone 1

Milestone ini menyiapkan struktur awal ERP modular.

## Prinsip

- Project `ERP_SO` dan `Nota` hanya dipakai sebagai referensi.
- Sales Order menjadi pusat ERP.
- Modul Nota disiapkan untuk terhubung ke Sales Order memakai `so_id`.
- Login sementara berbasis session memiliki role `admin` dan `produksi`.
- Modul Nota hanya dapat dibuka oleh role `admin`.
- Customer approval nanti memakai public token, bukan login dashboard.

