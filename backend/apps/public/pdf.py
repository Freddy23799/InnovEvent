from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

from apps.documents.pdf_utils import INNOVEVENT_NAVY, INNOVEVENT_RED, draw_footer, draw_header, draw_info_table, new_canvas


def build_pack_preview_pdf(pack, lines, total) -> bytes:
    """Aperçu tarifaire d'un pack, généré sans authentification depuis la page
    publique — volontairement sommaire (pas de conditions, pas de QR, pas de
    numéro de devis) et marqué « non contractuel » : le devis définitif exige
    un compte, via la demande de devis structurée du pack."""
    width, height = A4
    buffer, pdf = new_canvas(A4)
    table_width = width - 36 * mm

    draw_header(pdf, width, title="Aperçu tarifaire (non contractuel)", subtitle=pack.label)

    # Bandeau d'avertissement — impossible de confondre cet aperçu avec un vrai devis.
    banner_y = height - 42 * mm
    pdf.setFillColor(HexColor("#FBF0DC"))
    pdf.rect(18 * mm, banner_y - 14 * mm, table_width, 14 * mm, fill=True, stroke=False)
    pdf.setFillColor(HexColor("#A66A00"))
    pdf.setFont("Helvetica-Bold", 9.5)
    pdf.drawString(22 * mm, banner_y - 6 * mm, "APERÇU NON CONTRACTUEL")
    pdf.setFont("Helvetica", 8.5)
    pdf.drawString(22 * mm, banner_y - 11 * mm, "Créez un compte gratuit pour recevoir un devis définitif, structuré et signé par nos prestataires.")

    rows_top = banner_y - 24 * mm
    if lines:
        row_height = 8 * mm
        rows = [(f"{line['name']} × {line['quantity']}", f"{line['subtotal']:,.0f} XAF".replace(",", " ") if line["subtotal"] is not None else "Sur devis") for line in lines]
        draw_info_table(pdf, 18 * mm, rows_top, table_width, rows, row_height=row_height)
        table_bottom = rows_top - len(rows) * row_height

        band_y = table_bottom - 6 * mm
        pdf.setFillColor(INNOVEVENT_RED)
        pdf.rect(18 * mm, band_y - 10 * mm, table_width, 10 * mm, fill=True, stroke=False)
        pdf.setFillColor(HexColor("#FFFFFF"))
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(22 * mm, band_y - 6.8 * mm, "TOTAL ESTIMATIF")
        pdf.drawRightString(18 * mm + table_width - 4 * mm, band_y - 6.8 * mm, f"{total:,.0f} XAF".replace(",", " "))
    else:
        pdf.setFillColor(INNOVEVENT_NAVY)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(18 * mm, rows_top - 8 * mm, "Aucun élément sélectionné.")

    draw_footer(pdf, width, "Cet aperçu ne constitue pas un engagement contractuel — les prix peuvent varier selon vos options finales.")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
