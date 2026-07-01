# API and Routes

Dokumen ini mencatat endpoint penting yang tersedia dan yang direncanakan. ERP saat ini masih berorientasi server-rendered HTML, bukan public REST API.

## Authentication

| Method | Endpoint | Status | Keterangan |
| --- | --- | --- | --- |
| GET/POST | `/auth/login` | Active | Login user internal. |
| GET | `/auth/logout` | Active | Logout user internal. |
| GET/POST | `/login` | Active | Alias login. |

## Dashboard

| Method | Endpoint | Status | Keterangan |
| --- | --- | --- | --- |
| GET | `/dashboard/` | Active | Dashboard internal. Login required. |
| GET | `/master-data` | Active | Alias ke Master Data SO. Admin required. |
| GET | `/laporan` | Active | Alias ke Laporan SO. Admin required. |
| GET | `/laporan/pdf` | Active | Alias PDF laporan SO. Admin required. |
| GET | `/setting` | Active | Alias ke Setting SO. Admin required. |

## Sales Order

| Method | Endpoint | Status | Keterangan |
| --- | --- | --- | --- |
| GET | `/sales-order/` | Active | Daftar Sales Order. |
| GET/POST | `/sales-order/create` | Active | Create Sales Order. Admin required. |
| GET | `/sales-order/<sales_order_id>` | Active | Detail Sales Order, termasuk tombol Buat/Lihat Nota untuk admin dan status penagihan sederhana. |
| GET/POST | `/sales-order/<sales_order_id>/edit` | Active | Edit Sales Order. Admin required. |
| POST | `/sales-order/<sales_order_id>/delete` | Active | Delete Sales Order. Admin required. |
| GET | `/sales-order/<sales_order_id>/print` | Active | Print view Sales Order. Admin required. |
| GET | `/sales-order/<sales_order_id>/pdf` | Active | PDF Sales Order. Admin required. |
| POST | `/sales-order/<sales_order_id>/production-status` | Active | Update status produksi. |
| POST | `/sales-order/<sales_order_id>/production-checklist` | Active | Update checklist produksi. |
| POST | `/sales-orders/<sales_order_id>/approve-admin` | Active | Approval admin. |

## Sales Order Shell

| Method | Endpoint | Status | Keterangan |
| --- | --- | --- | --- |
| GET | `/production/` | Active | Daftar produksi SO approved. Admin required. |
| GET | `/production/<sales_order_id>` | Active | Detail produksi foundation dari ERP_SO. Admin required. |
| GET/POST | `/master/brands` | Active | Master brand SO. Admin required. |
| GET/POST | `/master/items` | Active | Master item SO. Admin required. |
| GET/POST | `/master/materials` | Active | Master material SO. Admin required. |
| GET/POST | `/master/patterns` | Active | Master pola SO. Admin required. |
| GET/POST | `/master/instructions` | Active | Master instruksi SO. Admin required. |
| GET/POST | `/master/users` | Active | Master user. Admin required. |
| GET | `/reports/` | Active | Laporan produksi SO. Admin required. |
| GET | `/reports/pdf` | Active | PDF laporan produksi SO. Admin required. |
| GET/POST | `/settings/` | Active | Setting target point bulanan. Admin required. |

## Nota

| Method | Endpoint | Status | Keterangan |
| --- | --- | --- | --- |
| GET | `/nota/dashboard` | Active | Dashboard keuangan Nota. Admin required. |
| GET | `/nota/` | Active | Daftar Nota. Admin required. |
| GET/POST | `/nota/baru` | Active | Create Nota manual atau dari Sales Order melalui query `so_id`. Admin required. |
| GET | `/nota/<nota_id>` | Active | Detail Nota, termasuk link balik ke Sales Order jika `so_id` terisi. Admin required. |
| GET/POST | `/nota/<nota_id>/edit` | Active | Edit Nota. Admin required. |
| POST | `/nota/<nota_id>/pembayaran` | Active | Tambah pembayaran Nota. Admin required. |
| POST | `/nota/<nota_id>/status` | Active | Ubah status Nota. Admin required. |
| GET | `/nota/<nota_id>/print` | Active | Print view Nota. Admin required. |
| GET | `/nota/<nota_id>/pdf/internal` | Active | PDF Nota internal. Admin required. |
| GET | `/nota/<nota_id>/pdf/customer` | Active | PDF invoice customer. Admin required. |
| GET/POST | `/nota/produk` | Active | Database produk Nota. Admin required. |
| GET | `/nota/produk/delete/<product_id>` | Active | Hapus produk Nota. Admin required. |
| GET | `/nota/laporan` | Active | Laporan keuangan Nota. Admin required. |
| GET | `/nota/laporan/customer` | Active | Laporan customer Nota. Admin required. |
| GET | `/nota/piutang` | Active | Laporan piutang Nota. Admin required. |
| GET | `/nota/pemasukan` | Active | Laporan pemasukan Nota. Admin required. |
| GET | `/nota/export/nota` | Active | Export semua Nota ke Excel. Admin required. |
| GET | `/nota/export/piutang` | Active | Export piutang ke Excel. Admin required. |
| GET | `/nota/export/omset-bulanan` | Active | Export omset bulanan ke Excel. Admin required. |
| GET | `/nota/export/customer` | Active | Export customer ke Excel. Admin required. |

## Customer Portal

| Method | Endpoint | Status | Keterangan |
| --- | --- | --- | --- |
| GET | `/tracking/<access_code>` | Foundation | Saat ini redirect ke Sales Order list. Full portal Planned. |
| GET | `/customer/sales-order/<token>` | Planned | Approval page customer. |
| POST | `/customer/sales-order/<token>/approve` | Planned | Customer approve Sales Order. |
| POST | `/customer/sales-order/<token>/revision` | Planned | Customer submit revisi. |

## Planned API

Endpoint REST/API untuk integrasi eksternal masih Planned:

- API Sales Order.
- API Nota.
- API Customer Portal.
- API AI assistant.
- API dashboard analytics.
