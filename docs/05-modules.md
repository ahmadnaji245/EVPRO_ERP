# ERP Modules

## Ringkasan Modul

| Modul | Status | Keterangan |
| --- | --- | --- |
| Sales Order | Completed | Core module untuk SO, desain, player, approval dasar, print/PDF, revisi, dashboard SO, produksi, master data, laporan, setting, dan status penagihan sederhana. |
| Invoice / Nota | Completed | CRUD Nota, dashboard keuangan, produk, laporan, piutang, pemasukan, export Excel, PDF customer/internal, dan integrasi ke Sales Order melalui `so_id`. |
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
- Print/PDF memakai brand asli Sales Order, tanpa mapping invoice.
- Dashboard SO.
- Produksi.
- Master Data.
- Laporan dan PDF laporan produksi.
- Setting target point bulanan.

ERP v0.2.2 menambahkan script import master data Sales Order dari ERP_SO untuk brand, logo brand, item, material, pola, instruksi, dan user. Kode brand ERP_SO dipakai sebagai singkatan brand; tampilan nomor SO pada modul Nota untuk brand non-FF/RDR memakai format `EV-{kode_brand}`.

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
- PDF internal.
- PDF customer.
- Admin-only access.
- Create Nota dari Sales Order.
- Prefill data customer dan item dasar dari Sales Order jika memungkinkan.
- Pencegahan satu Sales Order memiliki lebih dari satu Nota.
- Dashboard keuangan.
- Database produk.
- Laporan, piutang, pemasukan, dan export Excel.
- Mapping invoice brand untuk print Nota: FF Apparel -> FF Apparel, RDR Apparel -> layout Evpro dengan identitas RDR Apparel, brand lain -> Evpro.

Belum selesai:

- PDF lama brand-specific.
- Laporan finance lengkap.

## Production

Status: Foundation Active.

Saat ini tersedia halaman Produksi dari ERP_SO untuk daftar SO approved. Modul Production penuh dengan tracking proses lanjutan tetap direncanakan pada ERP v0.5.

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
