from io import BytesIO


def render_first_pdf_page_to_jpg(pdf_buffer, dpi=300, quality=95):
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF belum terpasang. Install dependency PyMuPDF untuk export JPG.") from exc

    if hasattr(pdf_buffer, "seek"):
        pdf_buffer.seek(0)
    pdf_bytes = pdf_buffer.getvalue() if hasattr(pdf_buffer, "getvalue") else pdf_buffer.read()

    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = document.load_page(0)
        scale = dpi / 72
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False, colorspace=fitz.csRGB)
        try:
            jpg_bytes = pixmap.tobytes("jpeg", jpg_quality=quality)
        except TypeError:
            jpg_bytes = pixmap.tobytes("jpeg")
    finally:
        document.close()

    output = BytesIO(jpg_bytes)
    output.seek(0)
    return output
