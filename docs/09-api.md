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

## Nota

| Method | Endpoint | Status | Keterangan |
| --- | --- | --- | --- |
| GET | `/nota/` | Active | Daftar Nota. Admin required. |
| GET/POST | `/nota/baru` | Active | Create Nota manual atau dari Sales Order melalui query `so_id`. Admin required. |
| GET | `/nota/<nota_id>` | Active | Detail Nota, termasuk link balik ke Sales Order jika `so_id` terisi. Admin required. |
| GET/POST | `/nota/<nota_id>/edit` | Active | Edit Nota. Admin required. |
| POST | `/nota/<nota_id>/pembayaran` | Active | Tambah pembayaran Nota. Admin required. |
| POST | `/nota/<nota_id>/status` | Active | Ubah status Nota. Admin required. |
| GET | `/nota/<nota_id>/print` | Active | Print view Nota. Admin required. |

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
