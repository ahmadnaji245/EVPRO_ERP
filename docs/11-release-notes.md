# Release Notes

## ERP v0.1 - Framework

Status: Completed.

Fitur selesai:

- Struktur awal Flask ERP.
- Konfigurasi aplikasi.
- Database layer SQLAlchemy.
- Auth dasar dengan Flask-Login.
- Dashboard foundation.
- Blueprint registration.
- Struktur folder modular.
- Dokumentasi milestone awal.

## ERP v0.2 - Sales Order Module

Status: Completed.

Fitur selesai:

- Sales Order list.
- Create Sales Order.
- Edit Sales Order.
- Detail Sales Order.
- Delete Sales Order.
- Print/PDF Sales Order.
- Brand relation.
- Desain dan player.
- Customer access code foundation.
- Approval admin.
- Revision history foundation.
- Production status foundation.
- Production checklist foundation.

## ERP v0.3 - Invoice / Nota Module

Status: Completed.

Fitur selesai:

- SQLAlchemy model Nota.
- SQLAlchemy model NotaItem.
- SQLAlchemy model NotaPayment.
- SQLAlchemy model NotaProduct.
- SQLAlchemy model NotaCustomer.
- Service layer Nota.
- Nomor Nota otomatis.
- Daftar Nota.
- Create Nota.
- Edit Nota.
- Detail Nota.
- Tambah pembayaran.
- Ubah status Nota.
- Print view Nota.
- Filter daftar Nota.
- Admin-only access.
- Role produksi tidak dapat membuka Nota.
- `so_id` nullable sebagai persiapan ERP v0.4.

## ERP v0.4 - SO ↔ Nota Integration

Status: Completed.

Fitur selesai:

- Relasi aktif Nota ke Sales Order melalui `so_id`.
- Tombol `Buat Nota` pada detail Sales Order jika belum ada Nota.
- Tombol `Lihat Nota` pada detail Sales Order jika Nota sudah dibuat.
- Prefill customer, tim, brand, tanggal, catatan, dan item dasar Nota dari Sales Order jika memungkinkan.
- Pencegahan Nota ganda untuk satu Sales Order di UI dan backend.
- Detail Nota menampilkan nomor Sales Order terkait dan tombol `Lihat Progress SO`.
- List Nota menampilkan informasi Sales Order terkait.
- List/detail Sales Order menampilkan status penagihan sederhana.
- Access control Nota tetap admin-only; role produksi tidak dapat membuka Nota.
- Migrasi ringan startup untuk memastikan kolom/index `notas.so_id` tersedia pada database development lama.

## Next Release

ERP v0.5 akan fokus pada Production Module lanjutan.
