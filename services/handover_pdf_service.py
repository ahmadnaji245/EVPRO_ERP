from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from services.handover_service import handover_period_label
from utils.formatters import pretty_date, pretty_datetime, rupiah


INK = colors.HexColor("#111827")
GRID = colors.HexColor("#cbd5e1")
HEADER = colors.HexColor("#f1f5f9")


def build_pending_handover_pdf(rows, printed_at=None):
    printed_at = printed_at or datetime.now()
    headers = [
        "No",
        "Nama Tim",
        "Brand",
        "Tanggal Finish",
        "Total Nota",
        "DP",
        "Sisa Tagihan",
        "Status Nota",
    ]
    data = [headers]
    for index, row in enumerate(rows, start=1):
        order = row["order"]
        data.append(
            [
                index,
                _p(order.team_name),
                _p(order.brand.code if order.brand else "-"),
                pretty_date(row["finish_at"]),
                rupiah(row["nota"]["total"]),
                rupiah(row["nota"]["paid"]),
                rupiah(row["nota"]["remaining"]),
                _p(row["nota"]["status"]),
            ]
        )
    return _build_pdf(
        title="Laporan Serah Terima Belum Diambil",
        subtitle="Semua SO Finish Produksi yang belum memiliki tanggal pengambilan",
        printed_at=printed_at,
        table=_table(data, [8 * mm, 46 * mm, 20 * mm, 24 * mm, 24 * mm, 22 * mm, 24 * mm, 22 * mm], right_align_cols=(4, 5, 6)),
    )


def build_picked_handover_pdf(rows, month, year, printed_at=None):
    printed_at = printed_at or datetime.now()
    headers = [
        "No",
        "Tanggal Ambil",
        "Diambil Oleh",
        "Nama Tim",
        "Brand",
        "Status Nota",
        "Catatan",
    ]
    data = [headers]
    for index, row in enumerate(rows, start=1):
        order = row["order"]
        data.append(
            [
                index,
                pretty_date(row["pickup_date"]),
                _p(row["picked_by"]),
                _p(order.team_name),
                _p(order.brand.code if order.brand else "-"),
                _p(row["nota"]["status"]),
                _p(row["note"]),
            ]
        )
    return _build_pdf(
        title="Laporan Serah Terima Sudah Diambil",
        subtitle=f"Periode: {handover_period_label(month, year)}",
        printed_at=printed_at,
        table=_table(data, [8 * mm, 25 * mm, 32 * mm, 45 * mm, 20 * mm, 24 * mm, 36 * mm]),
    )


def _build_pdf(title, subtitle, printed_at, table):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=title,
    )
    styles = _styles()
    story = [
        Paragraph(_e(title), styles["TitleText"]),
        Paragraph(_e(subtitle), styles["MetaText"]),
        Paragraph(f"Tanggal Cetak: {_e(pretty_datetime(printed_at))}", styles["MetaText"]),
        Spacer(1, 5 * mm),
        table,
    ]
    doc.build(story)
    buffer.seek(0)
    return buffer


def _table(data, widths, right_align_cols=()):
    if len(data) == 1:
        data.append(["-" for _ in data[0]])
    table = Table(data, colWidths=widths, repeatRows=1)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), INK),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for column in right_align_cols:
        commands.append(("ALIGN", (column, 1), (column, -1), "RIGHT"))
    table.setStyle(TableStyle(commands))
    return table


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleText",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=INK,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MetaText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CellText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=INK,
        )
    )
    return styles


def _p(value):
    return Paragraph(_e(value), _styles()["CellText"])


def _e(value):
    return escape(str(value or "-")).replace("\n", "<br/>")
