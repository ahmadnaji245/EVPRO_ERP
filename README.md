# EVPRO ERP

EVPRO ERP adalah sistem ERP modular untuk operasional garment dan custom jersey.

## Status Project

Repository ini adalah repository utama pengembangan EVPRO ERP.

Repository lama:
- `ERP_SO` = source of truth modul Sales Order
- `ERP-Nota` = source of truth modul Nota

Semua pengembangan baru dilakukan di repository ini.

## Core Architecture

Sales Order adalah pusat utama ERP.

Setiap modul operasional akan dihubungkan melalui `SO_ID`.

Contoh alur:

Customer → Sales Order → Approval → Produksi → Nota → Payment

## Release Roadmap

- ERP v0.1 ✅ Framework ERP
- ERP v0.2 ✅ Sales Order Module
- ERP v0.2.1 ✅ Complete Sales Order Module Migration
- ERP v0.2.2 ✅ Import Sales Order Master Data
- ERP v0.3 ✅ Invoice / Nota Module
- ERP v0.3.1 ✅ Complete Nota Module Migration
- ERP v0.4 ✅ SO ↔ Nota Integration Stable Development
- ERP v0.5 ✅ Production Management
- ERP v0.6 ⏳ Role & Permission
- ERP v0.7 ⏳ Customer Portal
- ERP v0.8 ⏳ CRM
- ERP v0.9 ⏳ AI Integration
- ERP v1.0 ⏳ Stable Internal Release

## Current Focus

Status saat ini:

EVPRO ERP sudah memiliki modul utama:
- Sales Order
- Nota / Invoice
- Integrasi SO ↔ Nota
- Master Data Sales Order
- Master Data Nota
- Role dasar admin dan produksi

Pengembangan berikutnya:

ERP v0.6 — Role & Permission

## Brand Logic

### Sales Order

Sales Order selalu menggunakan brand asli.

Contoh:
- Armor tetap Armor
- RDR tetap RDR
- FF tetap FF
- Evpro tetap Evpro

### Nota

Nota menggunakan aturan invoice brand:

- FF Apparel memakai template Nota FF
- RDR Apparel memakai template Nota Evpro dengan identitas/logo RDR
- Semua brand selain FF dan RDR masuk ke group EVPRO

Contoh:
- Armor di Nota ditampilkan sebagai sub-brand EVPRO
- Format tampilan dapat menggunakan `EV-{SINGKATAN}`

## Access Control

- Admin dapat mengakses Sales Order dan Nota
- Produksi tidak boleh mengakses Nota
- Customer tidak masuk dashboard ERP
- Customer nantinya hanya mengakses approval/progress melalui secure token

## ERP v0.5 — Production Management

ERP v0.5 sudah difokuskan pada Production Management.

Target:
- Dashboard produksi
- Antrian produksi dari SO
- Status produksi
- Tracking pekerjaan
- Integrasi dengan SO dan Nota

Status ERP v0.5:
- Dashboard Production Management aktif di halaman Produksi.
- Vendor produksi tersedia: Mas Amar dan Mas Syukron.
- Deadline vendor terpisah dari deadline customer/SO.
- Status produksi baru tersedia dari Menunggu Assign sampai Selesai.
- Barang masuk gudang dan QC/checklist internal tetap terhubung ke Surat Order.

## Next Milestone

ERP v0.6 akan difokuskan pada Role & Permission granular.
