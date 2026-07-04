# EVPRO TEXTILE ERP

**Integrated ERP System for Custom Apparel Manufacturing**

EVPRO ERP adalah sistem ERP internal untuk perusahaan custom apparel yang mengintegrasikan seluruh proses bisnis mulai dari Sales Order, Produksi, Nota, hingga Serah Terima. Sistem ini dirancang untuk membantu operasional produksi garment berjalan lebih terstruktur, terdokumentasi, dan terhubung antar divisi.

## Current Status

| Item | Status |
| --- | --- |
| Current Version | ERP v0.6 Role & Permission |
| Release Date | July 2026 |
| Repository Status | Main ERP Repository |

## Completed Features

### ✅ ERP v0.1 Framework

- [x] Login
- [x] Dashboard
- [x] Project Structure

### ✅ ERP v0.2 Sales Order

- [x] Surat Order
- [x] Approval Customer
- [x] PDF SO
- [x] Customer Database

### ✅ ERP v0.3 Nota

- [x] Invoice
- [x] Pembayaran Bertahap
- [x] Piutang
- [x] Produk

### ✅ ERP v0.4 Integrasi

- [x] Integrasi SO ↔ Nota
- [x] Dashboard
- [x] Laporan

### ✅ ERP v0.5 Production Management

- [x] Production Dashboard
- [x] Vendor Assignment
- [x] Printing
- [x] Jahit
- [x] QC
- [x] Packing
- [x] Finish
- [x] Vendor Production List
- [x] Vendor PDF Report
- [x] Vendor JPG Export
- [x] QC Portal
- [x] Dynamic Item
- [x] Dynamic QC
- [x] Serah Terima
- [x] Automatic Nota Status
- [x] Handover Report
- [x] Monthly Filter

### ✅ ERP v0.6 Role & Permission

- [x] Role user: admin, desain, produksi
- [x] Persistent login / remember session
- [x] Middleware permission untuk proteksi route backend
- [x] Sidebar/menu berbasis role
- [x] Admin bisa akses semua modul
- [x] Desain bisa melihat Surat Order, detail, checklist setting/desain, dan Serah Terima
- [x] Produksi bisa melihat Surat Order, produksi, assignment vendor, checklist produksi, PDF vendor, dan Serah Terima
- [x] Desain dan produksi diblokir dari create/edit/delete data utama Surat Order dan Nota
- [x] Customer Portal tetap public-token based melalui `/tracking/<token>`
- [x] Token Customer Portal untuk SO baru menggunakan token unik acak, bukan ID berurutan

## Workflow

```text
Surat Order
↓
Approval Customer
↓
Setting
↓
Printing
↓
Jahit
↓
QC
↓
Packing
↓
Finish
↓
Serah Terima
↓
Nota Lunas
```

## Roadmap

- [x] v0.1 Framework
- [x] v0.2 Sales Order
- [x] v0.3 Nota
- [x] v0.4 Integration
- [x] v0.5 Production Management
- [x] v0.6 Role & Permission
- [ ] v0.7 Customer Portal
- [ ] v0.8 CRM
- [ ] v0.9 AI Integration
- [ ] v1.0 Stable Release

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | Python, Flask |
| Database | SQLite |
| Frontend | Bootstrap 5, Jinja2 |
| PDF Export | ReportLab |
| Version Control | Git, GitHub |

## Module Overview

| Module | Description |
| --- | --- |
| Sales Order | Membuat, mengelola, dan mencetak Surat Order produksi. |
| Production Management | Mengatur alur produksi dari assignment vendor sampai finish. |
| Nota | Mengelola invoice, pembayaran bertahap, piutang, dan status nota. |
| Serah Terima | Mencatat barang yang belum dan sudah diambil, termasuk laporan PDF/JPG. |
| Reports | Menyediakan laporan operasional untuk monitoring internal. |

## Role & Permission

Default user ERP v0.6:

| Username | Password | Role |
| --- | --- | --- |
| admin | admin | admin |
| desain | desain | desain |
| produksi | produksi | produksi |

Ringkasan akses:

| Role | Akses |
| --- | --- |
| Admin | Semua halaman dan aksi: Dashboard, Surat Order, Produksi, Nota, Master Data, Laporan, Setting, dan User. |
| Desain | Login internal, lihat Surat Order/detail, update checklist setting/desain, lihat Serah Terima. Tidak bisa membuat/edit data utama SO atau Nota. |
| Produksi | Login internal, lihat Surat Order/detail, update checklist produksi, assign vendor/deadline vendor, cetak PDF vendor, akses Serah Terima dan laporan pengambilan. Tidak bisa membuat/edit data utama SO atau Nota. |
| Customer/Konsumen | Tidak login dashboard internal. Akses hanya lewat public link/token untuk melihat SO, approve SO, melihat Nota, dan progress produksi. |

Session login staff dibuat persisten dengan remember cookie dan lifetime panjang. Login ulang diperlukan saat logout manual, token/session di-reset, atau setelah maintenance/update yang mengganti secret/session aplikasi.

## Development Notes

Repository ini adalah source utama pengembangan EVPRO ERP setelah rilis ERP v0.6 Role & Permission.

```text
EVPRO ERP v0.6 Role & Permission
Release: July 2026
Focus: Role-based access control, persistent login, secure customer token portal
```
