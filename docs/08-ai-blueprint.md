# AI Blueprint

## Prinsip AI ERP

AI pada EVPRO ERP dirancang sebagai intelligence layer yang membantu setiap modul ERP. AI bukan chatbot umum dan bukan pengganti workflow ERP.

AI menggunakan ChatGPT API untuk membaca konteks data ERP yang diizinkan, menghasilkan insight, rekomendasi, ringkasan, dan draft tindakan.

## Roadmap AI

### AI CRM

Status: Planned.

Target:

- Segmentasi customer.
- Rekomendasi follow-up.
- Deteksi repeat order.
- Ringkasan riwayat customer.

### AI Marketing

Status: Planned.

Target:

- Ide campaign.
- Draft pesan promosi.
- Analisis produk/brand yang sering dipesan.
- Rekomendasi audience.

### AI Dashboard

Status: Planned.

Target:

- Ringkasan performa bisnis.
- Insight dari Sales Order dan Nota.
- Deteksi trend omzet, produksi, dan piutang.

### AI Production

Status: Planned.

Target:

- Prediksi bottleneck produksi.
- Prioritas order berdasarkan deadline.
- Ringkasan status produksi.

### AI Inventory

Status: Planned.

Target:

- Prediksi kebutuhan bahan.
- Low stock recommendation.
- Forecast berdasarkan repeat order.

### AI Business Assistant

Status: Planned.

Target:

- Tanya data ERP dalam batas permission.
- Ringkasan harian.
- Draft laporan internal.
- Rekomendasi tindakan.

## Batasan

- AI harus mengikuti role permission.
- AI tidak boleh membuka data lintas role tanpa izin.
- AI tidak boleh langsung mengubah data penting tanpa approval user.
- AI output harus dianggap rekomendasi, bukan keputusan final.
