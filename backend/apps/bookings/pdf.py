from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas

from apps.documents.pdf_utils import draw_footer, draw_header, draw_info_table, draw_qr_image, draw_status_badge
from apps.documents.qr_utils import build_qr_png_bytes
from apps.documents.signing import sign_payload


def build_booking_receipt_pdf(booking) -> bytes:
    width, height = A4
    buffer = BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=A4)
    payment = booking.payment

    draw_header(pdf, width, title="Reçu de réservation", subtitle=payment.transaction_ref if payment else "")

    pdf.setFillColor(HexColor("#323232"))
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(18 * mm, height - 45 * mm, "REÇU DE PAIEMENT")

    draw_status_badge(pdf, width - 50 * mm, height - 48 * mm, booking.get_status_display(), active=True)

    table_width = width - 36 * mm
    rows = [
        ("Événement", booking.event.title),
        ("Ressource réservée", str(booking.resource)),
    ]
    resource = booking.resource
    if resource is not None and hasattr(resource, "average_rating"):
        avg = resource.average_rating()
        count = resource.review_count()
        rows.append(("Niveau (avis clients)", f"{avg:.1f} / 5 ★ ({count} avis)" if avg is not None else "Pas encore d'avis"))
    rows += [
        ("Période", f"{booking.start_datetime:%d/%m/%Y %H:%M} — {booking.end_datetime:%d/%m/%Y %H:%M}"),
        ("Durée facturée", f"{booking.duration_days} jour(s)"),
    ]
    if payment:
        rows += [
            ("Mode de paiement", payment.get_provider_display()),
            ("Référence de transaction", payment.transaction_ref),
            ("Date de paiement", f"{payment.completed_at:%d/%m/%Y %H:%M}" if payment.completed_at else "—"),
        ]
    draw_info_table(pdf, 18 * mm, height - 58 * mm, table_width, rows)

    amount_y = height - 58 * mm - len(rows) * 8 * mm - 12 * mm
    currency = payment.currency if payment else "XAF"
    pdf.setFillColor(HexColor("#C0272D"))
    pdf.rect(18 * mm, amount_y - 4 * mm, table_width, 14 * mm, fill=True, stroke=False)
    pdf.setFillColor(HexColor("#FFFFFF"))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(22 * mm, amount_y + 1.5 * mm, "MONTANT PAYÉ")
    amount = booking.estimated_cost if booking.estimated_cost is not None else 0
    pdf.drawRightString(18 * mm + table_width - 4 * mm, amount_y + 1.5 * mm, f"{amount:,.0f} {currency}".replace(",", " "))

    qr_png = build_qr_png_bytes(sign_payload("booking-receipt", booking.id))
    qr_y = amount_y - 45 * mm
    draw_qr_image(pdf, ImageReader(BytesIO(qr_png)), 18 * mm, qr_y, size=32 * mm)
    pdf.setFillColor(HexColor("#6F7780"))
    pdf.setFont("Helvetica", 8)
    pdf.drawString(54 * mm, qr_y + 20 * mm, "Scannez ce code pour vérifier")
    pdf.drawString(54 * mm, qr_y + 15 * mm, "l'authenticité de ce reçu.")

    draw_footer(pdf, width, f"Reçu généré automatiquement le {booking.updated_at:%d/%m/%Y} — Document faisant office de preuve de paiement.")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
