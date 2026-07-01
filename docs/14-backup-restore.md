# Backup and Restore

## Strategi Backup

Backup harus mencakup:

- Source code.
- Database.
- Uploaded files.
- Configuration.
- Release notes.

## GitHub

Source code harus disimpan di Git repository.

Praktik:

- Commit per milestone.
- Tag release penting.
- Jangan commit secret.
- Jangan commit database production.

## Database Backup

Development saat ini dapat memakai SQLite. Production disarankan PostgreSQL.

Backup SQLite:

- Copy file database saat aplikasi berhenti atau gunakan backup command yang aman.
- Simpan berdasarkan tanggal.

Backup PostgreSQL:

```bash
pg_dump DATABASE_NAME > backup.sql
```

## Restore

Restore harus diuji secara berkala.

Langkah umum:

1. Stop aplikasi.
2. Backup kondisi saat ini.
3. Restore database dari backup.
4. Restore uploaded files.
5. Jalankan aplikasi.
6. Verifikasi login, Sales Order, dan Nota.

## Import Produk Nota Legacy

Produk Nota lama tersimpan di database SQLite `../Nota/database/nota.sqlite3`, tabel `products`.
Kolom yang dipakai untuk import ke ERP adalah:

- `code` -> `nota_products.code`
- `description` -> `nota_products.description`
- `price` -> `nota_products.price`

Database lama tidak memiliki kolom brand, kategori, atau status aktif untuk produk, sehingga kolom tersebut tidak dimigrasikan.
Import dapat dijalankan ulang karena memakai `code` sebagai unique key: produk baru dibuat, sedangkan produk dengan kode yang sama diperbarui.

```bash
.venv/bin/python scripts/import_nota_products.py
```

Jika lokasi database lama berbeda:

```bash
.venv/bin/python scripts/import_nota_products.py --source-db /path/to/nota.sqlite3
```

## Import Master Data Sales Order Legacy

Master data Sales Order lama tersimpan di database SQLite `../ERP_SO/instance/erp_so.db`.
Script import membaca tabel berikut:

- `brands`
- `master_items`
- `master_materials`
- `master_patterns`
- `master_instructions`
- `users`

Jalankan:

```bash
.venv/bin/python scripts/import_so_master_data.py
```

Jika lokasi database ERP_SO berbeda:

```bash
.venv/bin/python scripts/import_so_master_data.py --source-db /path/to/erp_so.db
```

Import memakai strategi aman dan dapat dijalankan ulang. Data master dari ERP_SO dibuat atau diperbarui. Data contoh yang tidak ada di ERP_SO dihapus jika tidak dipakai transaksi. Jika brand/user lama masih direferensikan transaksi, data tersebut tidak dihapus paksa; brand akan dinonaktifkan agar relasi Sales Order/Nota tetap aman.

## Versioning

Gunakan format nama backup yang jelas:

```text
erp-backup-YYYYMMDD-HHMM.sql
erp-uploads-YYYYMMDD-HHMM.tar.gz
```

## Retention

Rekomendasi:

- Daily backup untuk 7 hari terakhir.
- Weekly backup untuk 4 minggu terakhir.
- Monthly backup untuk 12 bulan.

## Disaster Recovery

Dokumentasikan:

- Lokasi backup.
- Cara restore.
- Akun server.
- Dependency.
- Versi aplikasi.
