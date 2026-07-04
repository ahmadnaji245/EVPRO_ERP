# Business Workflow

## Workflow Utama

```text
Customer
    ↓
Surat Order
    ↓
Approval
    ↓
Production
    ↓
QC
    ↓
Packing
    ↓
Shipping
    ↓
Invoice / Nota
    ↓
Payment
    ↓
Repeat Order
```

## Penjelasan Tahap

### Customer

Customer mengirim kebutuhan order, desain, ukuran, jumlah, dan instruksi produksi.

### Surat Order

Admin membuat Surat Order sebagai dokumen pusat ERP. Secara internal route/model masih memakai nama `sales_order`, tetapi label operasional ditampilkan sebagai Surat Order. Surat Order menyimpan brand, customer/team, desain, player, deadline customer, instruksi, dan status produksi.

ERP v0.2.1 melengkapi workflow Surat Order dari ERP_SO:

- Dashboard SO menampilkan ringkasan point, status produksi, dan progress setting bulanan.
- Menu Surat Order menampilkan list/detail/create/edit SO.
- Produksi menampilkan dashboard Production Management untuk SO approved.
- Master Data mengelola brand, item, material, pola, instruksi, dan user.
- Laporan menampilkan laporan produksi per brand/periode dan PDF laporan.
- Setting mengelola target point bulanan.

### Approval

Approval dapat dilakukan oleh admin. Foundation customer approval berbasis access code sudah tersedia, sedangkan Customer Portal penuh masih Planned.

### Production Management

Surat Order menjadi dasar proses produksi. ERP v0.5 mengaktifkan Production Management pada halaman Produksi tanpa membuat portal/login vendor.

Alur Production Management:

- Admin/production controller membuka halaman Produksi.
- SO approved masuk ke antrian produksi.
- Admin assign vendor produksi ke `Mas Amar` atau `Mas Syukron`.
- Admin menentukan deadline vendor yang terpisah dari deadline customer/SO.
- Admin atau produksi memperbarui status produksi: Menunggu Assign, Dikirim ke Vendor, Sedang Diproduksi, Barang Masuk, QC, Packing, Selesai.
- Barang masuk gudang dicatat dari halaman Produksi.
- QC/checklist internal tetap memakai checklist produksi yang melekat pada Surat Order.
- Vendor eksternal tidak login ERP dan hanya menerima print/PDF Surat Order yang sudah ada.

Prioritas otomatis memakai deadline vendor jika tersedia. Jika belum ada deadline vendor, sistem memakai deadline customer/SO.

### QC

QC berada dalam alur produksi. Checklist QC tersedia pada Surat Order dan dibuka dari halaman Production Management.

### Packing

Packing adalah tahap akhir sebelum pengiriman dan menjadi salah satu status pada Production Management.

### Shipping

Shipping belum menjadi modul terpisah. Status ini masih Planned.

### Invoice / Nota

Nota dapat dibuat manual dari menu Nota atau sebagai dokumen turunan dari Surat Order. Pada ERP v0.4, admin dapat membuka detail Surat Order lalu memilih `Buat Nota`; sistem mengisi data customer dan item dasar dari Surat Order jika memungkinkan, lalu menyimpan relasi melalui `so_id`.

Jika Surat Order sudah memiliki Nota, tombol pada detail Surat Order berubah menjadi `Lihat Nota` dan pembuatan Nota ganda dicegah oleh backend.

ERP v0.3.1 melengkapi workflow Nota dari project Nota lama:

- Dashboard Nota menampilkan omset, piutang, pemasukan, status, dan grafik revenue.
- Produk mengelola database kode produk dan harga.
- Laporan menampilkan ringkasan keuangan, customer, serta export Excel.
- Piutang menampilkan Nota dengan sisa pembayaran aktif.
- Pemasukan menampilkan histori pembayaran.
- Detail Nota menyediakan PDF internal dan PDF customer.

Aturan brand print:

- Print/PDF Surat Order selalu memakai brand asli Surat Order.
- Print Nota memakai mapping invoice brand.
- Nota dari SO `Armor` memakai invoice Evpro.
- Nota dari SO `FF Apparel` memakai invoice FF Apparel.
- Nota dari SO `RDR Apparel` memakai layout invoice Evpro dengan identitas RDR Apparel.
- Nota dari brand lain selain FF Apparel dan RDR Apparel memakai invoice Evpro.

### Payment

Pembayaran dicatat pada Nota melalui `NotaPayment`. Status pembayaran/order dapat diubah oleh admin.

Status penagihan sederhana ditampilkan pada Surat Order:

- `Belum Ada Nota`
- `Nota Dibuat`
- `DP`
- `Lunas`

### Repeat Order

Repeat order dan follow-up customer akan masuk ke CRM pada ERP v0.8.

## Workflow Customer Portal

Customer Portal direncanakan sebagai akses eksternal terbatas.

```text
Admin membuat Surat Order
    ↓
Sistem membuat secure token / access code
    ↓
Customer membuka approval page
    ↓
Customer review desain dan detail order
    ↓
Customer approve atau memberi catatan revisi
    ↓
Admin dan produksi melihat status terbaru
```

Customer tidak login ke dashboard internal ERP.
