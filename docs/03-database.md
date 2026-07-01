# Database Documentation

## Database Layer

ERP memakai Flask-SQLAlchemy. Tabel dibuat melalui model SQLAlchemy dan saat ini masih memakai konfigurasi SQLite lokal untuk development.

## ERD Konseptual

```text
Users
  └── SalesOrder.created_by_id
  └── Nota.created_by_id

Brand
  └── SalesOrder.brand_id
  └── Nota.brand_id
  └── NotaCustomer.brand_id

SalesOrder
  ├── SalesOrderDesign
  │   └── SalesOrderPlayer
  │       └── ProductionChecklist
  ├── ProductionSizeChecklist
  ├── RevisionHistory
  ├── CustomerAccess
  ├── CustomerRevisionNote
  └── Nota.so_id

NotaCustomer
  └── Nota.customer_id

Nota
  ├── NotaItem
  └── NotaPayment
```

## Tabel Utama

### Users

Menyimpan user internal ERP.

Field penting:

- `id`
- `name`
- `username`
- `password_hash`
- `role`
- `is_active`

Role aktif saat ini: `admin`, `produksi`.

### SalesOrder

Core Business Object ERP.

Field penting:

- `id`
- `so_number`
- `brand_id`
- `team_name`
- `customer_code`
- `access_code`
- `approval_status`
- `production_status`
- `created_by_id`

`SalesOrder.id` adalah pusat relasi ERP.

### SalesOrderItem

Secara implementasi saat ini item Sales Order dipisahkan sebagai desain dan player:

- `SalesOrderDesign`
- `SalesOrderPlayer`

Konsep `SalesOrderItem` di dokumentasi merujuk pada detail item/desain/pemain yang melekat pada Sales Order.

### Nota

Menyimpan dokumen Nota / Invoice.

Field penting:

- `id`
- `nota_number`
- `brand_id`
- `order_date`
- `customer_id`
- `team_name`
- `status`
- `notes`
- `so_id`
- `created_by_id`

`so_id` bersifat nullable. Jika Nota dibuat dari Sales Order, `so_id` menyimpan `sales_orders.id`. Jika Nota dibuat manual dari menu Nota, `so_id` boleh kosong. Pada ERP v0.4, `so_id` dibuat unik untuk membatasi satu Sales Order hanya memiliki satu Nota.

### NotaItem

Menyimpan detail produk pada Nota.

Field penting:

- `nota_id`
- `product_id`
- `product_code`
- `description`
- `price`
- `quantity`
- `subtotal`

### NotaPayment

Menyimpan pembayaran Nota.

Field penting:

- `nota_id`
- `payment_date`
- `amount`
- `description`

### Brand

Menyimpan brand internal.

Field penting:

- `code`
- `name`
- `logo_path`
- `color`
- `point_per_size`
- `status`

### Customer

Status saat ini:

- `NotaCustomer` digunakan khusus modul Nota v0.3.
- `CustomerAccess` digunakan untuk akses customer berbasis token pada Sales Order.
- Model `Customer` umum untuk CRM masih Planned.

### Production

Status saat ini:

- Production foundation ada pada Sales Order melalui `production_status`, `ProductionChecklist`, dan `ProductionSizeChecklist`.
- Modul Production penuh masih Planned untuk ERP v0.5.

### Inventory

Inventory masih Planned.

### AuditLog

Audit log umum masih Planned. Saat ini riwayat revisi Sales Order ditangani oleh `RevisionHistory`.

## Relasi Penting

| Relasi | Status |
| --- | --- |
| Brand -> SalesOrder | Active |
| Brand -> Nota | Active |
| User -> SalesOrder | Active |
| User -> Nota | Active |
| SalesOrder -> SalesOrderDesign -> SalesOrderPlayer | Active |
| SalesOrder -> CustomerAccess | Active |
| SalesOrder -> RevisionHistory | Active |
| Nota -> NotaItem | Active |
| Nota -> NotaPayment | Active |
| SalesOrder -> Nota melalui `so_id` | Active |

## Migrasi Ringan v0.4

Saat aplikasi start, ERP memastikan tabel `notas` memiliki kolom `so_id` dan unique index untuk `so_id`. Ini menjaga database development v0.3 tetap dapat dipakai tanpa migrasi manual.
