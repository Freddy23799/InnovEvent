from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .pdf_utils import INNOVEVENT_NAVY, draw_footer, draw_header

_cell_style = ParagraphStyle(name="ReportCell", fontName="Helvetica", fontSize=8.5, leading=10.5)
_header_style = ParagraphStyle(name="ReportHeader", fontName="Helvetica-Bold", fontSize=8.5, leading=10.5, textColor=colors.white)


def build_table_report_pdf(title: str, headers: list, rows: list, subtitle: str = "") -> bytes:
    """Génère un rapport tabulaire de bout en bout (export de listes métier :
    événements, paiements, participants…), aux couleurs InnovEvent."""
    buffer = BytesIO()
    pagesize = landscape(A4)
    width, height = pagesize

    def _on_page(pdf, doc):
        draw_header(pdf, width, title=title, subtitle=subtitle or f"{len(rows)} ligne(s)", height=height)
        draw_footer(pdf, width, f"Rapport généré le {timezone.now():%d/%m/%Y à %H:%M}")

    doc = SimpleDocTemplate(
        buffer, pagesize=pagesize,
        topMargin=38 * mm, bottomMargin=22 * mm, leftMargin=14 * mm, rightMargin=14 * mm,
    )

    # Chaque cellule passe par Paragraph pour permettre le retour à la ligne
    # automatique des textes longs (évite tout chevauchement entre colonnes).
    header_row = [Paragraph(str(h), _header_style) for h in headers]
    body_rows = [[Paragraph(str(cell), _cell_style) for cell in row] for row in rows]
    table_data = [header_row] + body_rows

    col_count = len(headers)
    available_width = width - 28 * mm
    table = Table(table_data, colWidths=[available_width / col_count] * col_count, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INNOVEVENT_NAVY),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFBFC")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDE1E5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))

    elements = [Spacer(1, 2 * mm), table]
    doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)
    return buffer.getvalue()
