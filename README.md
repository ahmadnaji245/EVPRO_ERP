# EVPRO ERP

Integrated ERP System for Garment & Custom Jersey Industry.

## Project Vision

EVPRO ERP is an integrated web-based ERP platform developed specifically for garment and custom jersey manufacturing.

The system is modular and designed to grow over time.

Current Modules:

- Sales Order (Core Module)
- Invoice / Nota
- Production
- Inventory (Planned)
- Purchasing (Planned)
- Finance (Planned)
- CRM (Planned)
- AI Business Assistant (Planned)

## ERP Architecture

Sales Order (SO) is the primary business object.

Every operational module must be linked to a Sales Order through `SO_ID`.

## Roadmap

Roadmap pengembangan tersedia di [docs/roadmap.md](docs/roadmap.md).

Ringkasan milestone:

- ERP v0.1 ✅: Framework ERP
- ERP v0.2 ✅: Sales Order Module
- ERP v0.3: Invoice / Nota Module - Planned
- ERP v0.4: SO ↔ Nota Integration - Planned
- ERP v0.5: Production Module - Planned
- ERP v0.6: Role & Permission - Planned
- ERP v0.7: Customer Portal - Planned
- ERP v0.8: CRM - Planned
- ERP v0.9: AI Integration - Planned
- ERP v1.0: Stable Internal Release - Planned

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

Login sementara tidak memakai password. Pilih role `admin` untuk membuka modul Nota, atau `produksi` untuk akses dashboard dan Sales Order.
