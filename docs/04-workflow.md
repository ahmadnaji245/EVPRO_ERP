# Business Workflow

## Workflow Utama

```text
Customer
    ↓
Sales Order
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

### Sales Order

Admin membuat Sales Order sebagai dokumen pusat ERP. Sales Order menyimpan brand, customer/team, desain, player, deadline, instruksi, dan status produksi.

### Approval

Approval dapat dilakukan oleh admin. Foundation customer approval berbasis access code sudah tersedia, sedangkan Customer Portal penuh masih Planned.

### Production

Sales Order menjadi dasar proses produksi. Saat ini status produksi dan checklist tersedia sebagai foundation. Modul Production penuh direncanakan pada ERP v0.5.

### QC

QC berada dalam alur produksi. Checklist QC tersedia sebagai foundation pada Sales Order.

### Packing

Packing adalah tahap akhir sebelum pengiriman. Tracking packing penuh direncanakan pada modul Production.

### Shipping

Shipping belum menjadi modul terpisah. Status ini masih Planned.

### Invoice / Nota

Nota dapat dibuat manual dari menu Nota atau sebagai dokumen turunan dari Sales Order. Pada ERP v0.4, admin dapat membuka detail Sales Order lalu memilih `Buat Nota`; sistem mengisi data customer dan item dasar dari Sales Order jika memungkinkan, lalu menyimpan relasi melalui `so_id`.

Jika Sales Order sudah memiliki Nota, tombol pada detail Sales Order berubah menjadi `Lihat Nota` dan pembuatan Nota ganda dicegah oleh backend.

### Payment

Pembayaran dicatat pada Nota melalui `NotaPayment`. Status pembayaran/order dapat diubah oleh admin.

Status penagihan sederhana ditampilkan pada Sales Order:

- `Belum Ada Nota`
- `Nota Dibuat`
- `DP`
- `Lunas`

### Repeat Order

Repeat order dan follow-up customer akan masuk ke CRM pada ERP v0.8.

## Workflow Customer Portal

Customer Portal direncanakan sebagai akses eksternal terbatas.

```text
Admin membuat Sales Order
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
