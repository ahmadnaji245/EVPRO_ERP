# Deployment Guide

## Local Development

Jalankan aplikasi dari root project ERP.

```bash
.venv/bin/python app.py
```

Default port:

```text
5003
```

Default URL:

```text
http://127.0.0.1:5003/login
```

## Local Server

Untuk penggunaan internal lokal:

- Pastikan virtual environment aktif.
- Install dependency dari `requirements.txt`.
- Jalankan aplikasi pada host `0.0.0.0`.
- Batasi akses jaringan jika belum production-ready.

## Ubuntu

Target deployment production:

- Ubuntu LTS.
- Python virtual environment.
- Gunicorn sebagai WSGI server.
- Nginx sebagai reverse proxy.
- PostgreSQL sebagai database production.

## Gunicorn

Contoh target:

```bash
gunicorn "app:app" --bind 127.0.0.1:5003
```

Konfigurasi final harus disesuaikan dengan environment server.

## Nginx

Nginx digunakan untuk:

- Reverse proxy ke Gunicorn.
- Static file serving.
- HTTPS termination.
- Request size limit untuk upload.

## PostgreSQL

SQLite cocok untuk development lokal. Production disarankan memakai PostgreSQL.

Target:

- Database terpisah per environment.
- User database dengan permission terbatas.
- Backup otomatis.

## VPS

Deployment VPS perlu:

- Firewall.
- HTTPS.
- Systemd service.
- Backup database.
- Monitoring log.

## Cloud

Cloud deployment Planned. Opsi:

- VPS managed.
- Container.
- Managed PostgreSQL.
- Object storage untuk upload.

## Environment Variables

Variable penting:

- `SECRET_KEY`
- `DATABASE_URL`
- `APP_HOST`
- `APP_PORT`
