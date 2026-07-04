from io import BytesIO
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

from flask import current_app
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.platypus import Flowable


INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#555f6f")
GRID = colors.HexColor("#c8ced6")
LIGHT = colors.HexColor("#f3f5f7")
CHECKBOX = "□"
CONTENT_WIDTH = 184 * mm

rl_config.canvas_basefontname = "Times-Roman"


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="SOTitle",
            parent=styles["Title"],
            fontName="Times-Bold",
            fontSize=20,
            leading=23,
            textColor=INK,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SOSubtitle",
            parent=styles["BodyText"],
            fontName="Times-Bold",
            fontSize=9,
            leading=11,
            textColor=MUTED,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SOLabel",
            parent=styles["BodyText"],
            fontName="Times-Bold",
            fontSize=7.5,
            leading=9,
            textColor=MUTED,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SOText",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=8.5,
            leading=10.5,
            textColor=INK,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SOTextBold",
            parent=styles["SOText"],
            fontName="Times-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            name="SOGrade",
            parent=styles["BodyText"],
            fontName="Times-Bold",
            fontSize=20,
            leading=17,
            textColor=INK,
            spaceAfter=2,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SOInstruction",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=16,
            leading=15,
            textColor=INK,
            alignment=TA_CENTER,
        )
    )
    return styles


def _paragraph(value, style):
    return Paragraph(str(value or "-").replace("\n", "<br/>"), style)


def _safe_paragraph(value, style):
    return Paragraph(escape(str(value or "-")).replace("\n", "<br/>"), style)


def _date(value):
    return value.strftime("%d/%m/%Y") if value else "-"


def _static_path(relative_path):
    if not relative_path:
        return None
    path = Path(current_app.static_folder) / relative_path
    return path if path.exists() else None


def _image_flowable(image_path, empty_label, max_width, max_height):
    path = _static_path(image_path)
    if not path:
        return _empty_box(empty_label, max_width, max_height)
    image = Image(str(path))
    ratio = min(max_width / image.imageWidth, max_height / image.imageHeight)
    image.drawWidth = image.imageWidth * ratio
    image.drawHeight = image.imageHeight * ratio
    return image


def _empty_box(label, width, height):
    table = Table([[Paragraph(label, _styles()["SOText"])]], colWidths=[width], rowHeights=[height])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, GRID),
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _brand_header(order, design, styles):
    logo_path = order.brand.logo_path if order.brand else None
    logo = _image_flowable(logo_path, order.brand.code if order.brand else "BRAND", 72 * mm, 26 * mm)
    left = Table(
        [
            [logo],
            [Spacer(1, 4 * mm)],
            [_paragraph(str(design.grade or order.grade or "-").upper(), styles["SOGrade"])],
            [Spacer(1, 4 * mm)],
            [_paragraph(str(order.instructions or "-").upper(), styles["SOInstruction"])],
        ],
        colWidths=[104 * mm],
    )
    left.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    right = Table(
        [
            [_paragraph(str(order.team_name or "-").upper(), styles["SOTitle"])],
            [Spacer(1, 3 * mm)],
            [_info_table(order, design, styles)],
        ],
        colWidths=[78 * mm],
    )
    right.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    header = Table([[left, right]], colWidths=[108 * mm, 82 * mm])
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return header


def _info_table(order, design, styles):
    rows = [
        ("No SO", order.so_number),
        ("Tanggal", _date(order.created_at)),
        ("Item", design.item_name),
        ("Bahan", design.material or order.material or "-"),
        ("Pola", design.pattern or order.pattern or "-"),
        ("Deadline", _date(design.deadline or order.deadline)),
    ]
    table = Table(
        [[_paragraph(label, styles["SOLabel"]), _paragraph(value, styles["SOTextBold"])] for label, value in rows],
        colWidths=[22 * mm, 56 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, GRID),
                ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def _note_box(title, text, styles):
    table = Table(
        [[Paragraph(title, styles["SOLabel"])], [_paragraph(text, styles["SOText"])]],
        colWidths=[86 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, GRID),
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _design_images(design, styles):
    label_style = styles["SOLabel"]
    widths = [92 * mm, 92 * mm]
    rows = [
        [Paragraph("GAMBAR ATASAN", label_style), Paragraph("GAMBAR CELANA", label_style)],
        [
            _image_flowable(design.display_top_image_path, "Belum ada gambar atasan", 88 * mm, 74 * mm),
            _image_flowable(design.bottom_image_path, "Belum ada gambar celana", 88 * mm, 74 * mm),
        ],
        [
            _note_box("CATATAN KHUSUS ATASAN", design.display_top_notes, styles),
            _note_box("CATATAN KHUSUS CELANA", design.bottom_notes, styles),
        ],
    ]
    table = Table(rows, colWidths=widths, hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _size_recap_flowables(design, styles):
    recap = design.size_recap
    flowables = []
    if recap["groups"]:
        active_groups = [group for group in ["Kids", "Women", "Reguler"] if recap["groups"].get(group)]
        tables = []
        for group in active_groups:
            tables.append(_size_table(group, recap["groups"][group], design.size_setting_done))
        wrapper = Table([tables], colWidths=[sum(table._argW) + 6 * mm for table in tables], hAlign="CENTER")
        wrapper.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        flowables.append(_centered_section("Rekap Size", wrapper, styles))

    if recap["long_sleeve"]:
        if flowables:
            flowables.append(Spacer(1, 3 * mm))
        flowables.append(
            _centered_section(
                "Lengan Panjang",
                _size_table("Size", recap["long_sleeve"], design.size_setting_done, h_align="CENTER"),
                styles,
            )
        )
    return flowables


def _centered_section(title, content, styles):
    table = Table(
        [[Paragraph(title, styles["SOTextBold"])], [content]],
        colWidths=[CONTENT_WIDTH],
        hAlign="CENTER",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 0),
            ]
        )
    )
    return table


def _size_table(first_header, rows, checked_lookup=None, h_align=None):
    checked_lookup = checked_lookup or (lambda size: False)
    data = [[first_header, "Qty", "setting"]]
    data.extend([[row["size"], row["qty"], PdfCheckbox(checked_lookup(row["size"]))] for row in rows])
    data.append(["Total size", sum(row["qty"] for row in rows), PdfCheckbox(False)])
    table = Table(data, colWidths=[30 * mm, 11 * mm, 14 * mm], repeatRows=1, hAlign=h_align)
    table.setStyle(_compact_table_style())
    return table


def _compact_table_style():
    return TableStyle(
        [
            ("GRID", (0, 0), (-1, -1), 0.25, GRID),
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
            ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
            ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, -1), (-1, -1), "Times-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )


def _player_table(design, styles):
    header = ["NO", "NAMA", "NP", "SIZE", "KETERANGAN", "Setting", "cek"]
    rows = [header]
    for index, player in enumerate(design.players, start=1):
        setting = PdfCheckbox(True) if (
            player.checklist and player.checklist.setting_done
        ) else PdfCheckbox(False)
        cek = PdfCheckbox(True) if (
            player.checklist and player.checklist.qc_done
        ) else PdfCheckbox(False)
        rows.append(
            [
                index,
                _paragraph(player.player_name, styles["SOText"]),
                player.player_number or "-",
                player.size,
                _paragraph(player.notes or "-", styles["SOText"]),
                setting,
                cek,
            ]
        )
    if len(rows) == 1:
        rows.append(["-", "Belum ada player", "-", "-", "-", PdfCheckbox(False), PdfCheckbox(False)])

    table = Table(
        rows,
        repeatRows=1,
        colWidths=[10 * mm, 42 * mm, 16 * mm, 42 * mm, 35 * mm, 18 * mm, 18 * mm],
        hAlign="CENTER",
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, GRID),
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 0), (3, -1), "CENTER"),
                ("ALIGN", (5, 1), (6, -1), "CENTER"),
                ("VALIGN", (5, 1), (6, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def build_sales_order_pdf(order):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=order.so_number,
    )
    styles = _styles()
    story = []

    for index, design in enumerate(order.designs):
        if index:
            story.append(PageBreak())
        story.append(_brand_header(order, design, styles))
        story.append(Spacer(1, 4 * mm))
        story.append(_design_images(design, styles))
        story.append(Spacer(1, 4 * mm))
        for flowable in _size_recap_flowables(design, styles):
            story.append(flowable)
        if design.size_recap["groups"] or design.size_recap["long_sleeve"]:
            story.append(Spacer(1, 4 * mm))
        story.append(_player_table(design, styles))

    doc.build(story)
    buffer.seek(0)
    return buffer


def _format_number(value):
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def _is_evpro_report_group(group):
    return str(group.get("brand") or "").strip().casefold() == "evpro"


def _report_table(group, styles):
    show_seller = _is_evpro_report_group(group)
    data = [["No", "Nama Tim", "Brand", "Seller", "Total Order", "Poin"]] if show_seller else [["No", "Nama Tim", "Brand", "Total Order", "Poin"]]
    for index, row in enumerate(group["rows"], start=1):
        report_row = [
            index,
            _safe_paragraph(row["team_name"], styles["SOText"]),
            _safe_paragraph(row["brand"], styles["SOText"]),
        ]
        if show_seller:
            report_row.append(_safe_paragraph(row["seller"], styles["SOText"]))
        report_row.extend([_format_number(row["total_order"]), _format_number(row["point"])])
        data.append(report_row)

    subtotal_row = [
            "",
            _safe_paragraph(f"Subtotal {group['brand']}", styles["SOTextBold"]),
            "",
        ]
    if show_seller:
        subtotal_row.append("")
    subtotal_row.extend([_format_number(group["total_order"]), _format_number(group["total_point"])])
    data.append(subtotal_row)

    table = Table(
        data,
        repeatRows=1,
        colWidths=[10 * mm, 54 * mm, 34 * mm, 34 * mm, 24 * mm, 24 * mm] if show_seller else [10 * mm, 70 * mm, 44 * mm, 28 * mm, 28 * mm],
        hAlign="CENTER",
    )
    subtotal_index = len(data) - 1
    total_start_col = 4 if show_seller else 3
    total_end_col = 5 if show_seller else 4
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, GRID),
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, subtotal_index), (-1, subtotal_index), LIGHT),
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTNAME", (0, subtotal_index), (-1, subtotal_index), "Times-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (total_start_col, 0), (total_end_col, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _grand_total_table(report, styles):
    table = Table(
        [
            [
                _safe_paragraph("Grand Total Semua Brand", styles["SOTextBold"]),
                _safe_paragraph("Total Order Semua Brand", styles["SOLabel"]),
                _format_number(report["grand_total_order"]),
                _safe_paragraph("Total Poin Semua Brand", styles["SOLabel"]),
                _format_number(report["grand_total_point"]),
            ]
        ],
        colWidths=[55 * mm, 40 * mm, 22 * mm, 40 * mm, 23 * mm],
        hAlign="CENTER",
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, GRID),
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("FONTNAME", (0, 0), (0, 0), "Times-Bold"),
                ("FONTNAME", (2, 0), (2, 0), "Times-Bold"),
                ("FONTNAME", (4, 0), (4, 0), "Times-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                ("ALIGN", (4, 0), (4, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def build_production_report_pdf(report, title="Laporan Sales Order Produksi"):
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
    story = [Paragraph(title, styles["SOTitle"]), Spacer(1, 6 * mm)]

    if not report["groups"]:
        story.append(_safe_paragraph("Belum ada data Sales Order.", styles["SOText"]))
    for index, group in enumerate(report["groups"]):
        if index:
            story.append(Spacer(1, 7 * mm))
        story.append(_safe_paragraph(group["brand"], styles["SOTextBold"]))
        story.append(Spacer(1, 2 * mm))
        story.append(_report_table(group, styles))

    story.append(Spacer(1, 8 * mm))
    story.append(_grand_total_table(report, styles))

    doc.build(story)
    buffer.seek(0)
    return buffer


def build_vendor_production_table_pdf(vendor, rows, quantity_columns, printed_at, deadline_class):
    buffer = BytesIO()
    title = f"DAFTAR PRODUKSI VENDOR - {str(vendor or '').upper()}"
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=8 * mm,
        leftMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
        title=title,
    )
    styles = _styles()
    story = [
        Paragraph(title, styles["SOTitle"]),
        Paragraph(f"Tanggal cetak: {printed_at.strftime('%d/%m/%Y %H:%M')}", styles["SOSubtitle"]),
        Spacer(1, 5 * mm),
    ]

    if not rows:
        story.append(_safe_paragraph("Belum ada order aktif untuk vendor ini.", styles["SOTextBold"]))
    else:
        story.append(_vendor_production_table(rows, quantity_columns, styles, deadline_class))

    doc.build(story)
    buffer.seek(0)
    return buffer


def build_order_production_list_pdf(rows):
    buffer = BytesIO()
    title = "LIST ORDER PRODUKSI"
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=8 * mm,
        leftMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
        title=title,
    )
    styles = _styles()
    story = [
        Paragraph(title, styles["SOTitle"]),
        Paragraph(f"Tanggal cetak: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}", styles["SOSubtitle"]),
        Spacer(1, 5 * mm),
    ]

    if not rows:
        story.append(_safe_paragraph("Belum ada order produksi.", styles["SOTextBold"]))
    else:
        story.append(_order_production_list_table(rows, styles))

    doc.build(story)
    buffer.seek(0)
    return buffer


def _order_production_list_table(rows, styles):
    header = [
        "No",
        "Tanggal Masuk Produksi",
        "Nama Tim",
        "Brand",
        "Vendor Jahit",
        "Setting Oleh",
        "Status Produksi",
        "Deadline Customer",
        "Deadline Vendor",
    ]
    data = [header]
    for index, row in enumerate(rows, start=1):
        data.append(
            [
                str(index),
                row["production_in_at"].strftime("%d/%m/%Y") if row["production_in_at"] else "-",
                _safe_paragraph(row["team_name"], styles["SOText"]),
                row["brand"],
                row["vendor"],
                _safe_paragraph(row["setting_by"], styles["SOText"]),
                row["status"],
                row["deadline_customer"].strftime("%d/%m/%Y") if row["deadline_customer"] else "-",
                row["deadline_vendor"].strftime("%d/%m/%Y") if row["deadline_vendor"] else "-",
            ]
        )
    table = Table(
        data,
        colWidths=[8 * mm, 25 * mm, 35 * mm, 14 * mm, 23 * mm, 25 * mm, 23 * mm, 24 * mm, 24 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#111827")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("ALIGN", (3, 0), (4, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _vendor_production_table(rows, quantity_columns, styles, deadline_class):
    header = ["NO", "NAMA TEAM", "STATUS", "MERK"]
    header.extend([_vendor_qty_label(component) for component in quantity_columns])
    header.extend(["TANGGAL MASUK", "DEADLINE JAHIT", "KETERANGAN"])

    data = [header]
    for index, row in enumerate(rows, start=1):
        line = [
            str(index),
            _safe_paragraph(row["team_name"], styles["SOText"]),
            _safe_paragraph(row["status"], styles["SOText"]),
            row["brand"],
        ]
        line.extend([str(row["qty"].get(component, 0)) for component in quantity_columns])
        line.extend(
            [
                row["assigned_at"].strftime("%d/%m/%Y") if row["assigned_at"] else "-",
                row["deadline"].strftime("%d/%m/%Y") if row["deadline"] else "-",
                _safe_paragraph(row["shortage_note"] or "-", styles["SOText"]),
            ]
        )
        data.append(line)

    qty_width = 13 * mm
    col_widths = [8 * mm, 34 * mm, 22 * mm, 14 * mm]
    col_widths.extend([qty_width] * len(quantity_columns))
    col_widths.extend([22 * mm, 22 * mm, 46 * mm])
    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")

    table_style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#111827")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.2),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("ALIGN", (4, 0), (3 + len(quantity_columns), -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]

    deadline_col = len(header) - 2
    for row_index, row in enumerate(rows, start=1):
        css_class = deadline_class(row["deadline"])
        if css_class == "deadline-late":
            table_style.extend(
                [
                    ("BACKGROUND", (deadline_col, row_index), (deadline_col, row_index), colors.HexColor("#dc2626")),
                    ("TEXTCOLOR", (deadline_col, row_index), (deadline_col, row_index), colors.white),
                    ("FONTNAME", (deadline_col, row_index), (deadline_col, row_index), "Times-Bold"),
                ]
            )
        elif css_class == "deadline-h1":
            table_style.extend(
                [
                    ("BACKGROUND", (deadline_col, row_index), (deadline_col, row_index), colors.HexColor("#f97316")),
                    ("TEXTCOLOR", (deadline_col, row_index), (deadline_col, row_index), colors.white),
                    ("FONTNAME", (deadline_col, row_index), (deadline_col, row_index), "Times-Bold"),
                ]
            )
        elif css_class == "deadline-h2":
            table_style.extend(
                [
                    ("BACKGROUND", (deadline_col, row_index), (deadline_col, row_index), colors.HexColor("#fde047")),
                    ("TEXTCOLOR", (deadline_col, row_index), (deadline_col, row_index), colors.HexColor("#111827")),
                    ("FONTNAME", (deadline_col, row_index), (deadline_col, row_index), "Times-Bold"),
                ]
            )

    table.setStyle(TableStyle(table_style))
    return table


def _vendor_qty_label(component):
    value = str(component or "").strip()
    if value.casefold() == "celana":
        return "QTY CLN"
    if value.casefold() == "jersey":
        return "QTY JRSY"
    return f"QTY {value.upper()}"


def build_placeholder_pdf(title):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    doc.build([Paragraph(title, getSampleStyleSheet()["Title"])])
    buffer.seek(0)
    return buffer

class PdfCheckbox(Flowable):
    def __init__(self, checked=False, size=4*mm):
        super().__init__()
        self.checked = checked
        self.size = size
        self.width = size
        self.height = size

    def draw(self):
        canvas = self.canv

        canvas.rect(
            0,
            0,
            self.size,
            self.size,
            stroke=1,
            fill=0,
        )

        if self.checked:
            canvas.setLineWidth(1.4)

            canvas.line(
                self.size*0.20,
                self.size*0.50,
                self.size*0.42,
                self.size*0.22
            )

            canvas.line(
                self.size*0.42,
                self.size*0.22,
                self.size*0.82,
                self.size*0.82
            )
