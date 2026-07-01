from io import BytesIO
import pathlib

from reportlab.lib import colors
from reportlab.lib import styles
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from utils.formatters import pretty_date, rupiah
from reportlab.platypus import Image

from pathlib import Path
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Image, Table, TableStyle

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

BRAND_CONFIG = {
    "Evpro": {
        "logo_path": BASE_DIR / "static/images/evpro_logo.png.png",
        "company_name": "EVPRO TEXTILE",
        "company_tagline": "Everything Production",
        "address": "Tegalsambi RT 09/RW 02 Tahunan, Jepara",
        "contact": "+6289 534 086 1234",
        "bank_info": "Bank BCA | 2470269301 | a/n. Muhammad Fahmi"
    },

    "RDR Apparel": {
        "logo_path": BASE_DIR / "static/images/rdr_logo.png.png",
        "company_name": "RDR Apparel",
        "company_tagline": "Get Ready Go Faster",
        "address": "Jl. Sunan Mantingan, Tegalsambi, Tahunan, Jepara",
        "contact": "+62858 7573 2969",
        "bank_info": "Bank BRI | 002201030118506 | a/n. Muhammad Fahmi"
    },
    
    "FF Apparel": {
        "logo_path": BASE_DIR / "static/images/ff_logo.png.png",
        "company_name": "FF Apparel",
        "company_tagline": "We Create, Not Only Make",
        "address": "Tegalsambi RT 09 RW 02, Tahunan, Jepara",
        "contact": "+62895 2616 0209",
        "bank_info": "Bank BRI | 002201030118506 | a/n. Muhammad Fahmi"
    }
    # Tambahkan konfigurasi untuk brand lain jika diperlukan
}


def _doc(buffer):
    return SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )


def _table(data, widths):
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c5162e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d9dce2")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f8fa")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (-3, 1), (-1, -1), "CENTER"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _summary_table(rows):
    table = Table(rows, colWidths=[110 * mm, 45 * mm])
    table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.6, colors.HexColor("#20242a")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def build_customer_invoice_pdf(invoice, items, totals):
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    story = []
    BASE_DIR = Path(__file__).resolve().parent.parent
    brand_info = BRAND_CONFIG[invoice["brand"]]
    logo_path = brand_info["logo_path"]

    title_style = ParagraphStyle(
        "TittleCustom",
        parent=styles["Normal"],
        fontsize=20,
        leading=24,
        fontName="Helvetica-Bold",
    )

    info_style = ParagraphStyle(
        "Infostyle",
        parent=styles["Normal"],
        fontsize=13,
        leading=18,
    )

    bold_style = ParagraphStyle(
        "Boldstyle",
        parent=styles["Normal"],
        fontsize=13,
        leading=18,
        fontName="Helvetica-Bold",
    )

    logo = Image(str(logo_path))
    logo._restrictSize(90 * mm, 32 * mm)

    left_data = [
        [logo],
        [Spacer(1, 4 * mm)],
        [Paragraph(brand_info["address"], title_style)],
        [Paragraph(f"WA. {brand_info['contact']}", info_style)],
        [Paragraph(brand_info["bank_info"], info_style)],
    ]

    right_data = [
        [Paragraph("<b>INVOICE</b>", title_style)],
        [Spacer(1,4)],

        [Paragraph(
            f"Nomor Nota : {invoice['invoice_number']}",
            info_style)],

        [Paragraph(
            f"Tanggal : {pretty_date(invoice['order_date'])}",
            info_style)],
        
        [Spacer(1,2)],

        [Paragraph("Kepada Yth.", info_style)],

        [Paragraph(
            f"<b>{invoice['customer_name']}</b>",
            bold_style)],

        [Paragraph(
            f"Team : {invoice['team_name']}",
            info_style)],

        [Paragraph(
            f"Alamat : {invoice['address'] or '-'}",
            info_style)],
        ]
    header_table = Table(
        [[left_data, right_data]],
        colWidths=[115 * mm, 70 * mm]
    )

    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(header_table)
    story.append(Spacer(1,8*mm))

    line = Table(
        [[""]],
        colWidths=[180 * mm]
    )

    line.setStyle(TableStyle([
        ("LINEABOVE", (0,0), (-1,-1), 2, colors.HexColor("#d10000"))
    ]))

    story.append(line)
    story.append(Spacer(1,5*mm))

    rows = [["NO", "DESCRIPTION", "QTY", "PRICE", "SUBTOTAL"]]
    for index, item in enumerate(items, start=1):
        rows.append(
            [
                index,
                item["description"],
                item["quantity"],
                rupiah(item["price"]),
                rupiah(item["subtotal"]),
            ]
        )
    story.append(_table(rows, [12 * mm, 83 * mm, 18 * mm, 35 * mm, 37 * mm]))
    story.append(Spacer(1, 6 * mm))
    story.append(
        _summary_table(
            [
                ["Total Nota", rupiah(totals["total"])],
                ["Sudah Dibayar", rupiah(totals["paid"])],
                ["Sisa Pembayaran", rupiah(totals["remaining"])],
            ]
        )
    )
    if invoice["notes"]:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(f"<b>Catatan:</b><br/>{invoice['notes']}", styles["Normal"]))

    story.append(Spacer(1, 12 * mm))

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        alignment=1,      # center
        fontSize=10,
        leading=16
    )

    story.append(
        Paragraph(
            f"""
            <b>Terima kasih atas kepercayaan Anda</b><br/><br/>
            {brand_info['company_name']} | {brand_info['company_tagline']}<br/>
            """,
            footer_style
        )
    )
    _doc(buffer).build(story)
    buffer.seek(0)
    return buffer


def build_internal_note_pdf(invoice, items, payments, totals):
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("<b>EVPRO</b>", styles["Title"]))
    story.append(Paragraph("EVERYTHING PRODUCTION", styles["Normal"]))
    story.append(
        Paragraph(
            f"""
            Nomor Nota: <b>{invoice['invoice_number']}</b><br/>
            Status Order: {invoice['status']}<br/>
            Brand: {invoice['brand']}<br/>
            Customer: {invoice['customer_name']} - {invoice['team_name']}<br/>
            Nomor HP: {invoice['phone'] or '-'}<br/>
            Alamat: {invoice['address'] or '-'}<br/>
            Tanggal Order: {pretty_date(invoice['order_date'])}
            """,
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 6 * mm))
    rows = [["Kode", "Keterangan", "Qty", "Harga", "Subtotal"]]
    for item in items:
        rows.append(
            [
                item["product_code"],
                item["description"],
                item["quantity"],
                rupiah(item["price"]),
                rupiah(item["subtotal"]),
            ]
        )
    story.append(_table(rows, [24 * mm, 75 * mm, 18 * mm, 35 * mm, 37 * mm]))
    story.append(Spacer(1, 7 * mm))
    story.append(Paragraph("<b>Histori Pembayaran</b>", styles["Heading3"]))
    payment_rows = [["Tanggal", "Nominal", "Keterangan"]]
    for payment in payments:
        payment_rows.append(
            [
                pretty_date(payment["payment_date"]),
                rupiah(payment["amount"]),
                payment["description"] or "-",
            ]
        )
    if len(payment_rows) == 1:
        payment_rows.append(["-", "-", "Belum ada pembayaran"])
    story.append(_table(payment_rows, [42 * mm, 45 * mm, 96 * mm]))
    story.append(Spacer(1, 6 * mm))
    story.append(
        _summary_table(
            [
                ["Total Nota", rupiah(totals["total"])],
                ["Sudah Dibayar", rupiah(totals["paid"])],
                ["Sisa Piutang", rupiah(totals["remaining"])],
            ]
        )
    )
    if invoice["notes"]:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(f"<b>Catatan:</b><br/>{invoice['notes']}", styles["Normal"]))
    _doc(buffer).build(story)
    buffer.seek(0)
    return buffer
