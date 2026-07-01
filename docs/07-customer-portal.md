# Customer Portal

## Konsep

Customer Portal adalah akses eksternal terbatas untuk customer. Customer tidak login ke ERP internal dan tidak melihat dashboard internal.

Customer hanya membuka halaman tertentu memakai secure token atau access code.

## Akses Customer

Customer dapat membuka:

- Approve SO.
- Progress produksi.
- Status pesanan.

Customer tidak boleh membuka:

- Dashboard internal.
- Daftar semua Sales Order.
- Modul Nota internal.
- Finance.
- Production checklist internal.
- Data customer lain.

## Status Saat Ini

Foundation access code sudah tersedia pada Sales Order. Full Customer Portal masih Planned untuk ERP v0.7.

## Target ERP v0.7

Fitur target:

- Public approval page.
- Secure token per Sales Order.
- Review desain.
- Approve atau request revision.
- Progress produksi yang aman untuk customer.
- Status pesanan.
- Catatan revisi dari customer.

## Prinsip Keamanan

- Token harus unik dan sulit ditebak.
- Token tidak boleh memberi akses ke dashboard internal.
- Data yang tampil harus dibatasi per Sales Order.
- Link customer harus dapat dinonaktifkan jika perlu.
