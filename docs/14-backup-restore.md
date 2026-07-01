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
