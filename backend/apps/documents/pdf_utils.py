import io

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .company import COMPANY_EMAIL, COMPANY_NAME, COMPANY_PHONE, COMPANY_WEBSITE, LOGO_PATH

INNOVEVENT_RED = HexColor("#C0272D")
INNOVEVENT_NAVY = HexColor("#39495B")
INNOVEVENT_LIGHT = HexColor("#F6E2E3")

_logo_reader = None


def _get_logo():
    global _logo_reader
    if _logo_reader is None:
        try:
            _logo_reader = ImageReader(LOGO_PATH)
        except Exception:
            _logo_reader = False
    return _logo_reader or None


def new_canvas(pagesize=A4):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=pagesize)
    return buffer, pdf


def draw_header(pdf, width, title, subtitle="", height=297 * mm):
    band_height = 30 * mm
    top = height
    pdf.setFillColor(INNOVEVENT_NAVY)
    pdf.rect(0, top - band_height, width, band_height, fill=True, stroke=False)

    logo = _get_logo()
    text_x = 18 * mm
    if logo:
        logo_size = 16 * mm
        pdf.drawImage(logo, 16 * mm, top - band_height + (band_height - logo_size) / 2, width=logo_size, height=logo_size, mask="auto")
        text_x = 16 * mm + logo_size + 4 * mm

    pdf.setFillColor(HexColor("#FFFFFF"))
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(text_x, top - 15 * mm, COMPANY_NAME)
    pdf.setFont("Helvetica", 10.5)
    pdf.drawString(text_x, top - 23 * mm, title)
    if subtitle:
        pdf.setFont("Helvetica", 8.5)
        pdf.drawRightString(width - 18 * mm, top - 23 * mm, subtitle)


def draw_footer(pdf, width, text):
    pdf.setFillColor(HexColor("#DDE1E5"))
    pdf.setLineWidth(0.5)
    pdf.line(18 * mm, 20 * mm, width - 18 * mm, 20 * mm)
    pdf.setFillColor(INNOVEVENT_NAVY)
    pdf.setFont("Helvetica", 7.5)
    pdf.drawCentredString(width / 2, 15 * mm, f"{COMPANY_NAME} — {COMPANY_PHONE} — {COMPANY_EMAIL} — {COMPANY_WEBSITE}")
    pdf.setFont("Helvetica", 7.5)
    pdf.drawCentredString(width / 2, 11 * mm, text)


def draw_qr_image(pdf, qr_image_reader, x, y, size=35 * mm):
    pdf.drawImage(qr_image_reader, x, y, width=size, height=size, mask="auto")


def draw_status_badge(pdf, x, y, label, active=True):
    color = INNOVEVENT_RED if active else HexColor("#6F7780")
    pdf.setFillColor(color)
    pdf.roundRect(x, y, 32 * mm, 8 * mm, 4, fill=True, stroke=False)
    pdf.setFillColor(HexColor("#FFFFFF"))
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawCentredString(x + 16 * mm, y + 2.6 * mm, label.upper())


def draw_info_table(pdf, x, y, width, rows, row_height=8 * mm):
    """Tableau bordé libellé/valeur, utilisé pour structurer les reçus et documents
    officiels (colonnes alignées, alternance de fond légère)."""
    for i, (label, value) in enumerate(rows):
        row_y = y - i * row_height
        if i % 2 == 0:
            pdf.setFillColor(HexColor("#FAFBFC"))
            pdf.rect(x, row_y - row_height, width, row_height, fill=True, stroke=False)
        pdf.setFillColor(INNOVEVENT_NAVY)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(x + 4 * mm, row_y - row_height + 2.8 * mm, str(label))
        pdf.setFillColor(HexColor("#323232"))
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(x + width - 4 * mm, row_y - row_height + 2.8 * mm, str(value))
    pdf.setStrokeColor(HexColor("#DDE1E5"))
    pdf.setLineWidth(0.7)
    pdf.rect(x, y - len(rows) * row_height, width, len(rows) * row_height, fill=False, stroke=True)
