# User Roles

## Prinsip Akses

Setiap route harus memiliki authentication dan authorization sesuai kebutuhan modul. Saat ini sistem memakai Flask-Login dengan role dasar.

## Role

### Owner

Status: Planned.

Hak akses target:

- Semua modul.
- Laporan bisnis.
- Finance.
- User management.
- AI insight.

### Admin

Status: Active.

Hak akses:

- Dashboard internal.
- Surat Order.
- Create/edit/delete Surat Order.
- Approval admin.
- Production Management.
- Assign vendor produksi.
- Set deadline vendor.
- Catat barang masuk gudang.
- Update status produksi dan checklist.
- Nota.
- Create/edit Nota.
- Tambah pembayaran.
- Ubah status Nota.

Admin boleh membuka modul Nota.

### Produksi

Status: Active.

Hak akses:

- Surat Order.
- Halaman Produksi / Production Management.
- Update production status/checklist sesuai kebutuhan operasional.
- Cetak PDF Surat Order untuk kebutuhan produksi/vendor.

Batasan:

- Produksi tidak boleh membuka route Nota.
- Produksi tidak boleh create/edit/delete Surat Order admin-only.
- Produksi tidak boleh assign vendor atau set deadline vendor jika tidak diberi role admin.

### Customer

Status: Planned untuk portal penuh.

Konsep akses:

- Customer tidak memiliki login dashboard ERP.
- Customer membuka halaman approval menggunakan secure token.
- Customer hanya dapat melihat informasi yang aman untuk eksternal.

Customer hanya boleh membuka approval page menggunakan secure token.

## Matriks Akses

| Modul / Aksi | Owner | Admin | Produksi | Customer |
| --- | --- | --- | --- | --- |
| Dashboard internal | Planned | Yes | Limited | No |
| Surat Order list/detail | Planned | Yes | Yes | No |
| Create/edit Surat Order | Planned | Yes | No | No |
| Nota | Planned | Yes | No | No |
| Production Management | Planned | Yes | Yes | No |
| Assign vendor/deadline vendor | Planned | Yes | No | No |
| Barang masuk gudang | Planned | Yes | Yes | No |
| Production checklist | Planned | Yes | Yes | No |
| Customer approval page | Planned | Limited | No | Token only |
| Role management | Planned | Planned | No | No |
