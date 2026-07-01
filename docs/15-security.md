# Security

## Authentication

ERP memakai Flask-Login untuk user internal.

Prinsip:

- Semua route internal harus login required.
- Password tidak boleh disimpan plaintext.
- Session harus memakai `SECRET_KEY` yang aman.

## Password Hash

Model `User` memakai password hash melalui Werkzeug.

Prinsip:

- Jangan log password.
- Jangan expose password hash.
- Gunakan password kuat untuk production.

## Authorization

Authorization saat ini berbasis role.

Role aktif:

- `admin`
- `produksi`

Admin boleh membuka Nota. Produksi tidak boleh membuka Nota.

## Role Permission

ERP v0.6 akan menambahkan Role & Permission lebih granular.

Target:

- Permission per modul.
- Permission per aksi.
- Owner/admin/finance/produksi/sales.
- Audit perubahan permission.

## Secure Customer Token

Customer tidak login dashboard internal.

Customer-facing page harus memakai secure token atau access code.

Prinsip:

- Token unik.
- Token sulit ditebak.
- Token dapat dinonaktifkan.
- Token hanya membuka data Sales Order terkait.

## CSRF

CSRF protection belum terdokumentasi sebagai fitur aktif. Untuk production, semua form POST harus dilindungi CSRF.

Status: Planned hardening.

## Audit Log

Audit log umum masih Planned.

Saat ini:

- Sales Order memiliki revision history foundation.

Target:

- Audit create/update/delete.
- Audit login.
- Audit payment.
- Audit status change.
- Audit permission change.

## Data Exposure

Prinsip:

- Jangan tampilkan data internal ke customer.
- Jangan expose route admin ke role produksi.
- Jangan expose file upload tanpa validasi.

## Production Security Checklist

- Set `SECRET_KEY` dari environment.
- Gunakan HTTPS.
- Gunakan database user terbatas.
- Backup database berkala.
- Batasi akses server.
- Aktifkan log.
- Tambahkan CSRF.
- Review route permission sebelum release.
