from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

from apps.documents.pdf_utils import (
    INNOVEVENT_NAVY,
    INNOVEVENT_RED,
    draw_footer,
    draw_header,
    draw_qr_image,
    draw_status_badge,
    new_canvas,
)
from apps.documents.qr_utils import build_qr_png_bytes
from apps.documents.signing import sign_payload

STATUS_LABELS_ACTIVE = {"accepted", "sent"}

BORDER_COLOR = HexColor("#DDE1E5")
TEXT_COLOR = HexColor("#323232")
MUTED_COLOR = HexColor("#6F7780")
STRIPE_COLOR = HexColor("#FAFBFC")
BOX_COLOR = HexColor("#F7F8FA")


def _fmt(amount, currency):
    return f"{amount:,.0f} {currency}".replace(",", " ")


def _draw_info_grid(pdf, x, y, width, pairs, row_height=11 * mm):
    """Grille 2 colonnes label/valeur — plus compacte qu'une colonne unique pour
    les 6 informations d'un devis (évite une longue table étroite avec beaucoup
    d'espace vide à droite). Spécifique à ce document : `draw_info_table` (une
    seule colonne) reste inchangé pour les autres PDF qui le partagent."""
    col_width = width / 2
    rows = (len(pairs) + 1) // 2
    for i, (label, value) in enumerate(pairs):
        row, col = divmod(i, 2)
        cell_x = x + col * col_width
        cell_y = y - row * row_height
        if row % 2 == 0:
            pdf.setFillColor(STRIPE_COLOR)
            pdf.rect(cell_x, cell_y - row_height, col_width, row_height, fill=True, stroke=False)
        pdf.setFillColor(MUTED_COLOR)
        pdf.setFont("Helvetica-Bold", 7.5)
        pdf.drawString(cell_x + 4 * mm, cell_y - 4.2 * mm, label.upper())
        pdf.setFillColor(INNOVEVENT_NAVY)
        pdf.setFont("Helvetica-Bold", 9.5)
        pdf.drawString(cell_x + 4 * mm, cell_y - row_height + 3 * mm, str(value))
    pdf.setStrokeColor(BORDER_COLOR)
    pdf.setLineWidth(0.7)
    pdf.rect(x, y - rows * row_height, width, rows * row_height, fill=False, stroke=True)
    pdf.line(x + col_width, y, x + col_width, y - rows * row_height)
    return y - rows * row_height


def _draw_items_table(pdf, x, y, width, items, currency):
    col_label = width - 70 * mm
    header_height = 9 * mm
    row_height = 8 * mm

    pdf.setFillColor(INNOVEVENT_NAVY)
    pdf.rect(x, y - header_height, width, header_height, fill=True, stroke=False)
    pdf.setFillColor(HexColor("#FFFFFF"))
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawString(x + 4 * mm, y - header_height + 3.2 * mm, "PRESTATION")
    pdf.drawCentredString(x + col_label + 15 * mm, y - header_height + 3.2 * mm, "QTÉ")
    pdf.drawRightString(x + col_label + 42 * mm, y - header_height + 3.2 * mm, "PRIX UNIT.")
    pdf.drawRightString(x + width - 4 * mm, y - header_height + 3.2 * mm, "TOTAL")

    cursor_y = y - header_height
    for i, item in enumerate(items):
        row_top = cursor_y
        if i % 2 == 0:
            pdf.setFillColor(STRIPE_COLOR)
            pdf.rect(x, row_top - row_height, width, row_height, fill=True, stroke=False)
        pdf.setFillColor(TEXT_COLOR)
        pdf.setFont("Helvetica", 8.5)
        pdf.drawString(x + 4 * mm, row_top - row_height + 2.8 * mm, item.label[:60])
        pdf.setFillColor(MUTED_COLOR)
        pdf.setFont("Helvetica", 8)
        pdf.drawCentredString(x + col_label + 15 * mm, row_top - row_height + 2.8 * mm, str(item.quantity))
        pdf.drawRightString(x + col_label + 42 * mm, row_top - row_height + 2.8 * mm, _fmt(item.unit_price, currency))
        pdf.setFillColor(TEXT_COLOR)
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawRightString(x + width - 4 * mm, row_top - row_height + 2.8 * mm, _fmt(item.line_total, currency))
        cursor_y -= row_height
        # Séparateur fin entre lignes — plus lisible qu'un simple alternat de fond
        # quand il y a beaucoup de prestations.
        pdf.setStrokeColor(BORDER_COLOR)
        pdf.setLineWidth(0.4)
        pdf.line(x, cursor_y, x + width, cursor_y)

    pdf.setStrokeColor(BORDER_COLOR)
    pdf.setLineWidth(0.7)
    pdf.rect(x, cursor_y, width, y - cursor_y, fill=False, stroke=True)
    return cursor_y


def _draw_totals_box(pdf, x, y, width, totals, total_label, total_amount, currency):
    """Bloc récapitulatif net et bordé (sous-total, frais, remise) surmonté du
    bandeau MONTANT TOTAL — remplace les lignes de texte flottantes non
    encadrées de l'ancienne version, qui se confondaient visuellement avec le
    reste de la page."""
    box_width = 85 * mm
    box_x = x + width - box_width
    line_height = 6.2 * mm
    padding_top = 5 * mm
    box_height = padding_top + len(totals) * line_height + 3 * mm

    if totals:
        pdf.setFillColor(BOX_COLOR)
        pdf.rect(box_x, y - box_height, box_width, box_height, fill=True, stroke=False)
        pdf.setStrokeColor(BORDER_COLOR)
        pdf.setLineWidth(0.7)
        pdf.rect(box_x, y - box_height, box_width, box_height, fill=False, stroke=True)

        cursor_y = y - padding_top - 3 * mm
        pdf.setFont("Helvetica", 8.5)
        for label, amount in totals:
            pdf.setFillColor(MUTED_COLOR)
            pdf.drawString(box_x + 5 * mm, cursor_y, label)
            pdf.setFillColor(TEXT_COLOR)
            pdf.setFont("Helvetica-Bold", 8.5)
            pdf.drawRightString(box_x + box_width - 5 * mm, cursor_y, _fmt(amount, currency))
            pdf.setFont("Helvetica", 8.5)
            cursor_y -= line_height

    band_y = y - box_height - 8 * mm
    pdf.setFillColor(INNOVEVENT_RED)
    pdf.rect(x, band_y - 5 * mm, width, 15 * mm, fill=True, stroke=False)
    pdf.setFillColor(HexColor("#FFFFFF"))
    pdf.setFont("Helvetica-Bold", 12.5)
    pdf.drawString(x + 5 * mm, band_y + 1 * mm, total_label)
    pdf.drawRightString(x + width - 5 * mm, band_y + 1 * mm, _fmt(total_amount, currency))
    return band_y - 5 * mm


def _draw_text_box(pdf, x, y, width, title, content, max_chars=95):
    """Encadré léger pour les conditions/annulation/message — au lieu d'un
    simple paragraphe qui se perdait dans le bas de page, chaque bloc est
    maintenant visuellement délimité, comme le reste du document."""
    lines = _wrap_text(content, max_chars)
    line_height = 4.6 * mm
    box_height = 8 * mm + len(lines) * line_height
    pdf.setFillColor(BOX_COLOR)
    pdf.rect(x, y - box_height, width, box_height, fill=True, stroke=False)
    pdf.setStrokeColor(BORDER_COLOR)
    pdf.setLineWidth(0.6)
    pdf.rect(x, y - box_height, width, box_height, fill=False, stroke=True)

    pdf.setFillColor(INNOVEVENT_NAVY)
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawString(x + 4 * mm, y - 5.5 * mm, title)
    text_y = y - 10.5 * mm
    pdf.setFillColor(HexColor("#4A4A4A"))
    pdf.setFont("Helvetica", 8)
    for line in lines:
        pdf.drawString(x + 4 * mm, text_y, line)
        text_y -= line_height
    return y - box_height


def build_quote_pdf(quote) -> bytes:
    width, height = A4
    buffer, pdf = new_canvas(A4)
    booking_request = quote.booking_request
    profile = booking_request.profile
    table_width = width - 36 * mm

    draw_header(pdf, width, title="Devis prestation événementielle", subtitle=f"Devis #{quote.pk:06d}")

    pdf.setFillColor(INNOVEVENT_NAVY)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(18 * mm, height - 44 * mm, profile.business_name)
    pdf.setFillColor(MUTED_COLOR)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(18 * mm, height - 49.5 * mm, f"{profile.category_display()} · {profile.city or 'Cameroun'}")

    draw_status_badge(
        pdf, width - 50 * mm, height - 48 * mm, quote.get_status_display(),
        active=quote.status in STATUS_LABELS_ACTIVE,
    )

    info_pairs = [
        ("Type d'événement", booking_request.event_type or "—"),
        ("Date souhaitée", booking_request.event_date.strftime("%d/%m/%Y") if booking_request.event_date else "—"),
        ("Ville", booking_request.city or "—"),
        ("Nombre d'invités", str(booking_request.guest_count) if booking_request.guest_count else "—"),
        ("Émis le", quote.created_at.strftime("%d/%m/%Y")),
        ("Valable jusqu'au", quote.valid_until.strftime("%d/%m/%Y") if quote.valid_until else "—"),
    ]
    info_bottom = _draw_info_grid(pdf, 18 * mm, height - 58 * mm, table_width, info_pairs)

    pdf.setFillColor(INNOVEVENT_NAVY)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(18 * mm, info_bottom - 8 * mm, "DÉTAIL DE LA PRESTATION")

    items_top = info_bottom - 12 * mm
    items = list(quote.items.all())
    items_bottom = _draw_items_table(pdf, 18 * mm, items_top, table_width, items, quote.currency)

    totals = [("Sous-total prestations", quote.items_total)]
    if quote.travel_fee:
        totals.append(("Frais de déplacement", quote.travel_fee))
    if quote.additional_fees:
        totals.append(("Frais supplémentaires", quote.additional_fees))
    if quote.discount:
        totals.append(("Remise", -quote.discount))

    band_bottom = _draw_totals_box(
        pdf, 18 * mm, items_bottom - 6 * mm, table_width, totals, "MONTANT TOTAL", quote.total_amount, quote.currency,
    )

    text_y = band_bottom - 8 * mm
    text_blocks = [
        (t, c) for t, c in (
            ("Conditions de prestation", quote.conditions),
            ("Conditions d'annulation", quote.cancellation_policy),
            ("Message du prestataire", quote.provider_note),
        ) if c
    ]
    for title, content in text_blocks:
        text_y = _draw_text_box(pdf, 18 * mm, text_y, table_width, title, content) - 5 * mm

    # QR de vérification — même principe que le reçu de réservation : un code
    # signé (jamais falsifiable) plutôt qu'une simple image décorative. Un
    # devis avec beaucoup de lignes et de texte peut ne plus laisser assez de
    # place en bas de page : plutôt que de forcer le QR à une position fixe
    # (et risquer un chevauchement avec le dernier encadré), on le reporte en
    # page 2 quand il ne reste pas assez de place.
    qr_size = 24 * mm
    qr_y = text_y - qr_size
    if qr_y < 24 * mm:
        draw_footer(pdf, width, "Ce devis est émis via la plateforme InnovEvent — aucun paiement ne doit être effectué hors plateforme.")
        pdf.showPage()
        draw_header(pdf, width, title="Devis prestation événementielle", subtitle=f"Devis #{quote.pk:06d}")
        qr_y = height - 70 * mm
    qr_png = build_qr_png_bytes(sign_payload("quote", quote.pk))
    draw_qr_image(pdf, ImageReader(BytesIO(qr_png)), 18 * mm, qr_y, size=qr_size)
    pdf.setFillColor(HexColor("#6F7780"))
    pdf.setFont("Helvetica", 8)
    pdf.drawString(18 * mm + qr_size + 5 * mm, qr_y + qr_size - 9 * mm, "Scannez ce code pour vérifier")
    pdf.drawString(18 * mm + qr_size + 5 * mm, qr_y + qr_size - 13.5 * mm, "l'authenticité de ce devis.")

    draw_footer(pdf, width, "Ce devis est émis via la plateforme InnovEvent — aucun paiement ne doit être effectué hors plateforme.")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _wrap_text(text, max_chars):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines
