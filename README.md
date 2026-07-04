# EVPRO TEXTILE ERP

**Integrated ERP System for Custom Apparel Manufacturing**

EVPRO ERP adalah sistem ERP internal untuk perusahaan custom apparel yang mengintegrasikan seluruh proses bisnis mulai dari Sales Order, Produksi, Nota, hingga Serah Terima. Sistem ini dirancang untuk membantu operasional produksi garment berjalan lebih terstruktur, terdokumentasi, dan terhubung antar divisi.

## Current Status

| Item | Status |
| --- | --- |
| Current Version | ERP v0.5 Stable |
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
- [ ] v0.6 Role & Permission
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

## Development Notes

Repository ini adalah source utama pengembangan EVPRO ERP setelah rilis ERP v0.5 Stable.

```text
EVPRO ERP v0.5 Stable
Release: July 2026
Focus: Production Management, Vendor Report, QC, Handover, and SO-Nota integration
```
