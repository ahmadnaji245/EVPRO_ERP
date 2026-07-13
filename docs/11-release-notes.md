# Release Notes

## ERP v0.1 - Framework

Status: Completed.

Fitur selesai:

- Struktur awal Flask ERP.
- Konfigurasi aplikasi.
- Database layer SQLAlchemy.
- Auth dasar dengan Flask-Login.
- Dashboard foundation.
- Blueprint registration.
- Struktur folder modular.
- Dokumentasi milestone awal.

## ERP v0.2 - Sales Order Module

Status: Completed.

Fitur selesai:

- Sales Order list.
- Create Sales Order.
- Edit Sales Order.
- Detail Sales Order.
- Delete Sales Order.
- Print/PDF Sales Order.
- Brand relation.
- Desain dan player.
- Customer access code foundation.
- Approval admin.
- Revision history foundation.
- Production status foundation.
- Production checklist foundation.

## ERP v0.2.1 - Complete Sales Order Module Migration

Status: Completed.

Fitur selesai:

- Dashboard SO dari ERP_SO.
- Menu bawah SO: Dashboard, Sales Order, Produksi, Master Data, Laporan, Setting.
- Halaman Produksi dari ERP_SO.
- Halaman Master Data untuk brand, item, material, pola, instruksi, dan user.
- Halaman Laporan dan PDF laporan produksi.
- Halaman Setting target point bulanan.
- Alias route lama: `/master-data`, `/laporan`, `/laporan/pdf`, dan `/setting`.
- Placeholder SO shell dihapus dan diganti fitur asli ERP_SO.
- Print/PDF SO tetap memakai jalur lama dan tidak diubah.

## ERP v0.2.2 - Import Sales Order Master Data

Status: Completed.

Fitur selesai:

- Script `scripts/import_so_master_data.py` untuk import ulang master data Sales Order dari ERP_SO.
- Import brand ERP_SO beserta kode/singkatan, logo, warna, point per size, status, dan catatan.
- Import master item, material, pola, dan instruksi dari ERP_SO.
- Import user ERP_SO dengan password hash Werkzeug yang kompatibel.
- Logo brand ERP_SO disalin ke `static/uploads/brands`.
- Seed data awal dibatasi hanya untuk database kosong agar tidak membuat ulang data contoh setelah import legacy.
- Format tampilan SO pada modul Nota untuk brand non-FF/RDR memakai `EV-{kode_brand}`.
- Brand lama yang sudah dipakai transaksi tidak dihapus paksa untuk menjaga foreign key Sales Order/Nota.

## ERP v0.3 - Invoice / Nota Module

Status: Completed.

Fitur selesai:

- SQLAlchemy model Nota.
- SQLAlchemy model NotaItem.
- SQLAlchemy model NotaPayment.
- SQLAlchemy model NotaProduct.
- SQLAlchemy model NotaCustomer.
- Service layer Nota.
- Nomor Nota otomatis.
- Daftar Nota.
- Create Nota.
- Edit Nota.
- Detail Nota.
- Tambah pembayaran.
- Ubah status Nota.
- Print view Nota.
- Filter daftar Nota.
- Admin-only access.
- Role produksi tidak dapat membuka Nota.
- `so_id` nullable sebagai persiapan ERP v0.4.

## ERP v0.3.1 - Complete Nota Module Migration

Status: Completed.

Fitur selesai:

- Dashboard keuangan Nota dari project Nota lama.
- Menu Nota: Dashboard, Nota, Nota Baru, Produk, Laporan, Piutang, Pemasukan.
- Database produk Nota.
- Laporan keuangan, customer, piutang, dan pemasukan.
- Export Excel untuk semua Nota, piutang, omset bulanan, dan customer.
- PDF Nota internal.
- PDF invoice customer dengan generator lama.
- Mapping PDF customer: FF Apparel memakai template FF, RDR Apparel memakai layout Evpro dengan identitas RDR Apparel, brand lain memakai Evpro.
- Semua route Nota tetap admin-only.
- Workflow SO ↔ Nota tetap dipertahankan.

## ERP v0.4 - SO ↔ Nota Integration

Status: Completed.

Fitur selesai:

- Relasi aktif Nota ke Sales Order melalui `so_id`.
- Tombol `Buat Nota` pada detail Sales Order jika belum ada Nota.
- Tombol `Lihat Nota` pada detail Sales Order jika Nota sudah dibuat.
- Prefill customer, tim, brand, tanggal, catatan, dan item dasar Nota dari Sales Order jika memungkinkan.
- Pencegahan Nota ganda untuk satu Sales Order di UI dan backend.
- Detail Nota menampilkan nomor Sales Order terkait dan tombol `Lihat Progress SO`.
- List Nota menampilkan informasi Sales Order terkait.
- List/detail Sales Order menampilkan status penagihan sederhana.
- Access control Nota tetap admin-only; role produksi tidak dapat membuka Nota.
- Migrasi ringan startup untuk memastikan kolom/index `notas.so_id` tersedia pada database development lama.
- Fix aturan brand print: Sales Order selalu memakai brand asli, sedangkan Nota memakai mapping invoice brand.
- Mapping invoice Nota: FF Apparel -> FF Apparel, RDR Apparel -> RDR Apparel, brand selain itu -> Evpro.

## ERP v0.5 - Production Management

Status: Completed.

Fitur selesai:

- Label tampilan menu Sales Order diubah menjadi Surat Order tanpa rename route/model/database internal.
- Menu atas menjadi Dashboard, Surat Order, Nota, Logout untuk admin.
- Menu bawah modul Surat Order menjadi Dashboard, Surat Order, Produksi, Master Data, Laporan, Setting.
- Halaman Produksi direvisi menjadi dashboard Production Management.
- Ringkasan produksi: Menunggu Assign, Sedang Diproduksi, Deadline Hari Ini, Barang Masuk / QC, Selesai, Terlambat.
- Ringkasan vendor untuk Mas Amar dan Mas Syukron.
- Assign vendor produksi dari SO approved.
- Deadline vendor terpisah dari deadline customer/SO.
- Status produksi sederhana: Menunggu Assign, Dikirim ke Vendor, Sedang Diproduksi, Barang Masuk, QC, Packing, Selesai.
- Mapping aman dari status produksi lama ke status baru.
- Catat Barang Masuk Gudang dari halaman Produksi.
- QC/checklist tetap memakai checklist produksi existing pada detail Surat Order.
- Cetak PDF Surat Order tetap memakai generator PDF SO existing tanpa perubahan layout.
- Prioritas otomatis berdasarkan deadline vendor atau deadline customer.
- Filter ketik untuk nomor SO, tim, brand, vendor, status, atau prioritas.
- Akses halaman Produksi dibuka untuk admin dan role produksi.
- Role produksi tetap tidak bisa mengakses Nota.
- Modul Nota, PDF Nota, integrasi SO ↔ Nota, dan output PDF SO tidak diubah.

## ERP v0.9 - Keuangan Kas Kecil

Status: Completed.

Fitur selesai:

- Modul Kas Kecil untuk mencatat uang tunai fisik EVPRO.
- Tambah Cash untuk saldo awal, penambahan modal, penjualan offline, pembayaran Nota Cash, pengembalian kasbon tunai, dan pemasukan lainnya.
- Integrasi pembayaran Nota dengan metode Cash dan Transfer.
- Pembayaran Nota Cash otomatis membuat pemasukan Kas Kecil.
- Pembayaran Nota Transfer tidak masuk Kas Kecil.
- Sinkronisasi perubahan pembayaran Nota ke transaksi Kas Kecil agar tidak tercatat dua kali.
- Master kategori pengeluaran Kas Kecil yang dapat diaktifkan, dinonaktifkan, dan diurutkan.
- Kelompok pengeluaran profesional untuk produksi, logistik, gaji/upah, konsumsi, administrasi, utilitas, pemeliharaan, kasbon, penyisihan tunjangan, transfer ke kas besar, prive, dan lainnya.
- Kasbon Karyawan tetap mengurangi Kas Kecil saat uang fisik keluar.
- Penyisihan Tunjangan tetap mengurangi Kas Kecil saat uang dipindahkan ke rekening tunjangan.
- Transfer ke Kas Besar dan Prive mengurangi Kas Kecil tetapi dipisahkan dari biaya operasional.
- Ringkasan Kas Kecil, Detail Kas Kecil, Pengeluaran Bulan Ini, dan Kategori Pengeluaran.
- PDF Ringkasan Kas Kecil dan PDF Detail Kas Kecil.
- Rekap pengeluaran berdasarkan kelompok dan subkategori.
- Void transaksi dan audit dasar untuk perubahan transaksi keuangan.
- Permission menu Keuangan dengan akses admin dan struktur role finance untuk pengembangan berikutnya.

## Next Release

ERP v0.10 akan fokus pada Integrasi AI setelah modul utama stabil.
