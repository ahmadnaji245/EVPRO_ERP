# ERP Modules

## Ringkasan Modul

| Modul | Status | Keterangan |
| --- | --- | --- |
| Sales Order | Completed | Core module untuk SO, desain, player, approval dasar, print/PDF, revisi, production checklist foundation, dan status penagihan sederhana. |
| Invoice / Nota | Completed | CRUD Nota, customer Nota, produk Nota, item, pembayaran, status, nomor otomatis, print view, dan integrasi ke Sales Order melalui `so_id`. |
| Production | Planned | Modul produksi penuh belum tersedia. Foundation status/checklist sudah ada di Sales Order. |
| Inventory | Planned | Stok bahan, stok produk, mutasi, dan kebutuhan produksi belum tersedia. |
| Finance | Planned | Laporan finance lengkap, piutang, pemasukan, dan integrasi accounting belum tersedia. |
| CRM | Planned | Customer database umum, follow-up, segmentasi, dan repeat order belum tersedia. |
| Dashboard | In Progress | Dashboard dasar tersedia. Dashboard analitik penuh masih Planned. |
| AI | Planned | AI integration belum tersedia. |

## Sales Order

Fitur selesai:

- Daftar Sales Order.
- Create/edit/detail/delete.
- Print/PDF.
- Approval admin.
- Customer access code foundation.
- Desain dan player.
- Production status foundation.
- Checklist produksi foundation.
- Tombol `Buat Nota` / `Lihat Nota` untuk admin.
- Status penagihan sederhana berdasarkan Nota terkait.

## Invoice / Nota

Fitur selesai:

- Daftar Nota.
- Create/edit/detail.
- Nota customer.
- Nota product.
- Item dan subtotal.
- Pembayaran.
- Status order/pembayaran.
- Print view.
- Admin-only access.
- Create Nota dari Sales Order.
- Prefill data customer dan item dasar dari Sales Order jika memungkinkan.
- Pencegahan satu Sales Order memiliki lebih dari satu Nota.

Belum selesai:

- PDF lama brand-specific.
- Laporan finance lengkap.

## Production

Status: Planned.

Target:

- Production order dari Sales Order.
- Progress produksi.
- QC dan packing.
- Target produksi.
- Status per tahap.

## Inventory

Status: Planned.

Target:

- Master bahan.
- Stok masuk/keluar.
- Kebutuhan produksi.
- Low stock alert.

## Finance

Status: Planned.

Target:

- Laporan piutang.
- Laporan pemasukan.
- Export Excel.
- Dashboard finance.

## CRM

Status: Planned.

Target:

- Customer database umum.
- Riwayat order.
- Follow-up.
- Segmentasi customer.

## Dashboard

Status: In Progress.

Saat ini tersedia dashboard modular dasar. Dashboard analitik penuh masih Planned.

## AI

Status: Planned.

AI akan membantu modul ERP, bukan menggantikan workflow ERP.
