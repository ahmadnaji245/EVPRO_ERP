# EVPRO ERP

Integrated ERP System for Garment & Custom Jersey Industry.

EVPRO ERP adalah repository utama untuk active development ERP modular EVPRO. Repository ini menjadi tempat integrasi bertahap dari modul Sales Order, Nota, Production, Inventory, Customer Portal, CRM, dan AI Business Assistant.

Repository lama `ERP_SO` dan `Nota` tetap diperlakukan sebagai stable source project / reference. Keduanya menjadi acuan perilaku modul lama, sedangkan pengembangan aktif dan integrasi dilakukan di repository EVPRO ERP ini.

## Project Vision

EVPRO ERP is an integrated web-based ERP platform developed specifically for garment and custom jersey manufacturing.

The system is modular and designed to grow over time.

Sales Order adalah primary business object. Semua modul operasional akan dihubungkan kembali ke Sales Order menggunakan `SO_ID`, sehingga proses order, nota, produksi, pembayaran, customer portal, CRM, dan insight bisnis tetap berpusat pada satu dokumen utama.

Completed modules:

- Framework ERP
- Sales Order Module
- Invoice / Nota Module

Next module:

- SO ↔ Nota Integration

Long-term direction:

- Production
- Inventory (Planned)
- Customer Portal (Planned)
- CRM (Planned)
- AI Business Assistant (Planned)

## ERP Architecture

Sales Order (SO) is the primary business object.

Every operational module must be linked to a Sales Order through `SO_ID`.

Integration direction:

```text
Sales Order
    -> Invoice / Nota
    -> Production
    -> Inventory
    -> Customer Portal
    -> CRM
    -> AI Business Assistant
```

## Roadmap

Roadmap pengembangan tersedia di [docs/roadmap.md](docs/roadmap.md).

Ringkasan milestone:

- ERP v0.1 ✅: Framework ERP
- ERP v0.2 ✅: Sales Order Module
- ERP v0.3 ✅: Invoice / Nota Module
- ERP v0.4 ⏳: SO ↔ Nota Integration - planned next
- ERP v0.5 ⏳: Production Module
- ERP v0.6 ⏳: Role & Permission
- ERP v0.7 ⏳: Customer Portal
- ERP v0.8 ⏳: CRM
- ERP v0.9 ⏳: AI Integration
- ERP v1.0 ⏳: Stable Internal Release

## Milestone 1 Scaffold

Struktur awal project:

```text
ERP/
├── app.py
├── config.py
├── database/
├── models/
├── routes/
│   ├── so_routes.py
│   └── nota_routes.py
├── templates/
│   ├── so/
│   └── nota/
├── static/
├── docs/
└── README.md
```

## Menjalankan Aplikasi

```bash
python app.py
```

Default URL:

- `http://127.0.0.1:5003/login`
- `http://127.0.0.1:5003/dashboard`

Default development login:

- Admin: `admin` / `admin`
- Produksi: `produksi` / `produksi`

Role `admin` dapat membuka Sales Order dan Nota. Role `produksi` hanya untuk akses operasional yang diizinkan dan tidak dapat membuka modul Nota internal.
