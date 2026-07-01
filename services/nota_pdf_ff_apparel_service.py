from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, 
    Paragraph, 
    SimpleDocTemplate, 
    Spacer, 
    Table, 
    TableStyle
)
from utils.formatters import pretty_date, rupiah

def build_ff_apparel_pdf(invoice, items, payments, totals):
    buffer = BytesIO()
    
    # Menggunakan A4 dengan margin 10mm agar area cetak maksimal (190mm lebar bersih)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )
    
    styles = getSampleStyleSheet()
    
    # Kustomisasi Style Teks untuk presisi visual
    style_info = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=15
    )
    
    style_note = ParagraphStyle(
        'NoteStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#212529")
    )
    
    story = []

    # 1. HEADER SECTION (Logo & Metadata)
    logo = Image("static/images/ff_logo.png.png", width=55 * mm, height=33 * mm)
    
    info_text = f"""
    Tanggal &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: {pretty_date(invoice["order_date"])}<br/>
    Nomor Order &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: {invoice["invoice_number"]}<br/>
    Nama Pemesan &nbsp;: {invoice["customer_name"]}<br/>
    Nama Tim &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: {invoice["team_name"]}<br/>
    No HP &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;:<br/>
    Alamat &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;:
    """
    info = Paragraph(info_text, style_info)

    header_table = Table([[logo, info]], colWidths=[105 * mm, 85 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (1,0), (1,0), 15 * mm), # Memberi space agar metadata rapi di kanan
    ]))
    story.append(header_table)
    story.append(Spacer(1, 5 * mm))

    # 2. GARIS MERAH PEMBATAS
    line = Table([[""]], colWidths=[190 * mm], rowHeights=[2])
    line.setStyle(TableStyle([
        ("LINEBELOW", (0,0), (-1,-1), 1.5, colors.HexColor("#DC3545")),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(line)
    story.append(Spacer(1, 5 * mm))

    # 3. TABEL UTAMA (RINCIAN PESANAN)
    # Header Tabel menggunakan Paragraph agar font tebal rata tengah bekerja sempurna
    th_no = Paragraph("<b>No</b>", styles['Normal'])
    th_desc = Paragraph("<b>Rincian Pesanan</b>", styles['Normal'])
    th_qty = Paragraph("<b>Qty</b>", styles['Normal'])
    th_harga = Paragraph("<b>Harga</b>", styles['Normal'])
    th_jumlah = Paragraph("<b>Jumlah</b>", styles['Normal'])
    
    rows = [[th_no, th_desc, th_qty, th_harga, th_jumlah]]
    
    for i, item in enumerate(items, start=1):
        rows.append([
            i,
            item["description"],
            item["quantity"],
            rupiah(item["price"]),
            rupiah(item["subtotal"])
        ])

    # Sesuai gambar asli, buat total baris kosong/isi di tabel menjadi sekitar 9 baris
    while len(rows) < 12:
        rows.append(["", "", "", "", ""])
            
    # Total lebar kolom harus pas 190 mm
    table = Table(rows, colWidths=[12 * mm, 83 * mm, 20 * mm, 37 * mm, 38 * mm], rowHeights=[22]*len(rows))
    table.setStyle(TableStyle([
        # Warna background header kuning soft sesuai gambar asli
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#FFF3CD")),
        # Grid tipis abu-abu di dalam tabel
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        # Alignment text per kolom
        ("ALIGN", (0,0), (0,-1), "CENTER"),    # No di tengah
        ("ALIGN", (1,0), (1,-1), "LEFT"),      # Rincian pesanan kiri
        ("ALIGN", (2,0), (2,-1), "CENTER"),    # Qty tengah
        ("ALIGN", (3,0), (3,-1), "CENTER"),    # Harga tengah
        ("ALIGN", (4,0), (4,-1), "CENTER"),    # Jumlah tengah
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
    ]))
    story.append(table)
    story.append(Spacer(1, 4 * mm))

    # 4. TABEL TOTAL & SISA PEMBAYARAN (Kanan Atas setelah Tabel)
    paid1 = payments[0]["amount"] if len(payments) >= 1 else 0
    paid2 = payments[1]["amount"] if len(payments) >= 2 else 0

    summary_rows = [
        ["Total", rupiah(totals["total"])],
        ["DP1", rupiah(paid1)],
        ["DP2", rupiah(paid2)],
        ["Sisa Pembayaran", rupiah(totals["remaining"])],
    ]

    summary_table = Table(summary_rows, colWidths=[45 * mm, 38 * mm], rowHeights=[18]*4)
    summary_table.setStyle(TableStyle([
        # Efek background kuning soft pada baris "Total" dan "Sisa Pembayaran"
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#FFF3CD")),
        ("BACKGROUND", (0,3), (-1,3), colors.HexColor("#FFF3CD")),
        # Border tipis pembatas summary
        ("LINEBELOW", (0,0), (-1,2), 0.5, colors.HexColor("#EAEAEA")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,3), (-1,3), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ALIGN", (0,0), (0,-1), "LEFT"),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))

    # Wrapper ditarik ke kanan pas dengan batas tabel utama
    summary_wrapper = Table([["", summary_table]], colWidths=[107 * mm, 83 * mm])
    summary_wrapper.setStyle(TableStyle([
        ("VALIGN", (1,0), (1,0), "TOP"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(summary_wrapper)
    story.append(Spacer(1, 4 * mm))

    # 5. REKENING & TANDA TANGAN SECTION
    rekening_kiri = Paragraph(
        """
        Desa Tegalsambi RT 09 RW 02<br/>
        Kecamatan Tahunan Kabupaten Jepara<br/><br/>
        Payment :<br/>
        <font color="#003399">
        BRI 002201030118506<br/>
        Kode 002<br/>
        A/n Muhammad Fahmi
        </font>
        """, style_info
    )
    
    rekening_tengah = Paragraph(
        """
        <br/><br/><br/><br/>
        <font color="#003399">
        Bank Jago 107724579160<br/>
        Kode 542<br/>
        A/n Muhammad Fahmi
        </font>
        """, style_info
    )
    
    ttd = Paragraph(
        """
        Hormat kami,<br/><br/><br/><br/>
        <b>FF_Apparel</b>
        """, style_info
    )

    footer_table = Table([[rekening_kiri, rekening_tengah, ttd]], colWidths=[75 * mm, 65 * mm, 50 * mm])
    footer_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (2,0), (2,0), "CENTER"), # Posisi Hormat Kami rata tengah
    ]))
    story.append(footer_table)
    story.append(Spacer(1, 8 * mm))

    # 6. BOX NOTE (CATATAN) DI BAGIAN PALING BAWAH
    note_content = """
    <b>Note:</b><br/>
    1. Khusus pesanan kaos (satuan/lusinan) originalitas desain bukan tanggung jawab kami.<br/>
    2. Garansi ganti barang baru hanya untuk pesanan dengan deadline mengikuti aturan.<br/>
    3. Seluruh kerusakan setelah pemakaian tidak masuk dalam tanggung jawab kami.<br/>
    4. Uang muka minimal 50%<br/>
    Ada potongan harga dengan ketentuan berlaku
    """
    note_p = Paragraph(note_content, style_note)
    
    # Membuat container ber-border melengkung (Rounded) untuk kolom Note
    note_table = Table([[note_p]], colWidths=[190 * mm])
    note_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#FFFDF5")),  # Soft ivory background
        ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#FFEBAA")),       # Soft border yellow
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
    ]))
    story.append(note_table)

    # Compile dokumen
    doc.build(story)
    buffer.seek(0)
    return buffer
