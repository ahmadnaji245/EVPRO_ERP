# EVPRO ERP Roadmap

## Visi EVPRO ERP

EVPRO ERP adalah sistem ERP modular untuk operasional garment dan custom jersey. Sistem ini dibangun agar proses dari Sales Order, approval customer, produksi, nota, pembayaran, sampai repeat order dapat berjalan dalam satu platform internal.

Prinsip utama:

- Sales Order menjadi pusat proses bisnis.
- Setiap modul dikembangkan bertahap agar stabil sebelum diintegrasikan.
- Modul internal dan customer-facing dipisahkan secara jelas.
- Fitur yang belum tersedia harus ditandai sebagai Planned, bukan dianggap selesai.

## Release Roadmap

| Version | Milestone | Status | Ringkasan |
| --- | --- | --- | --- |
| ERP v0.1 | Framework | Completed | Struktur Flask ERP, database layer, routing, template, auth dasar, dan modular scaffold. |
| ERP v0.2 | Sales Order | Completed | CRUD Sales Order, detail, print/PDF, approval dasar, desain, player, revisi, dan production checklist foundation. |
| ERP v0.2.1 | Complete Sales Order Module Migration | Completed | Dashboard SO, Produksi, Master Data, Laporan, Setting, route alias, dan menu bawah SO dimigrasikan dari ERP_SO. |
| ERP v0.3 | Invoice / Nota | Completed | CRUD Nota, item produk, customer Nota, pembayaran, status, nomor Nota otomatis, print view, dan admin-only access. |
| ERP v0.3.1 | Complete Nota Module Migration | Completed | Dashboard keuangan, produk, laporan, piutang, pemasukan, export Excel, dan PDF customer/internal dimigrasikan dari project Nota lama. |
| ERP v0.4 | SO ↔ Nota Integration | Completed | Relasi aktif Sales Order ke Nota melalui `so_id`, create Nota dari SO, pencegahan Nota ganda, dan status penagihan SO. |
| ERP v0.5 | Production | Planned | Modul produksi terpisah, tracking proses, target produksi, QC, packing, dan progress per SO. |
| ERP v0.6 | Role & Permission | Planned | Role granular, permission per modul, dan pembatasan akses selain admin/produksi. |
| ERP v0.7 | Customer Portal | Planned | Portal customer berbasis secure token untuk approval, progress, dan status pesanan. |
| ERP v0.8 | CRM | Planned | Customer database umum, riwayat order, follow-up, segmentasi, dan pipeline customer. |
| ERP v0.9 | AI Integration | Planned | AI assistant untuk CRM, dashboard, produksi, inventory, marketing, dan insight bisnis. |
| ERP v1.0 | Stable Internal Release | Planned | Rilis internal stabil dengan modul utama terintegrasi dan dokumentasi operasional. |

## Status Saat Ini

ERP saat ini berada pada tahap v0.4 dengan koreksi ERP v0.2.1 dan ERP v0.3.1 selesai. Modul Sales Order lengkap dari ERP_SO dan modul Nota lengkap dari project Nota lama sudah dimigrasikan, lalu keduanya terhubung melalui `nota.so_id`.
