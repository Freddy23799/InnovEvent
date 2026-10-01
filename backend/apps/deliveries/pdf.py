from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

from apps.documents.pdf_utils import (
    INNOVEVENT_NAVY,
    draw_footer,
    draw_header,
    draw_info_table,
    draw_qr_image,
    draw_status_badge,
    new_canvas,
)
from apps.documents.qr_utils import build_qr_png_bytes
from apps.documents.signing import sign_payload

STATUS_ACTIVE_LABELS = {"delivered"}


def build_delivery_note_pdf(delivery) -> bytes:
    """Bon de livraison — mêmes helpers que les devis/reçus existants
    (apps.documents.pdf_utils), avec un QR de vérification signé (même
    mécanisme que apps.bookings/apps.marketplace)."""
    width, height = A4
    buffer, pdf = new_canvas(A4)
    table_width = width - 36 * mm

    draw_header(pdf, width, title="Bon de livraison", subtitle=delivery.reference)

    pdf.setFillColor(INNOVEVENT_NAVY)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(18 * mm, height - 44 * mm, delivery.reference)
    draw_status_badge(
        pdf, width - 50 * mm, height - 48 * mm, delivery.get_status_display(),
        active=delivery.status in STATUS_ACTIVE_LABELS,
    )

    info_rows = [
        ("Code de suivi", delivery.tracking_code),
        ("Type", delivery.get_delivery_type_display()),
        ("Priorité", delivery.get_priority_display()),
        ("Départ", delivery.pickup_address),
        ("Destination", delivery.destination_address),
        ("Destinataire", delivery.recipient_name or "—"),
        ("Téléphone destinataire", delivery.recipient_phone or "—"),
        ("Transporteur", delivery.carrier.name if delivery.carrier else "—"),
        ("Chauffeur", delivery.driver.full_name if delivery.driver else "—"),
        ("Véhicule", delivery.vehicle.plate_number if delivery.vehicle else "—"),
        ("Montant", f"{delivery.amount:,.0f} XAF".replace(",", " ")),
        ("Mode de paiement", delivery.get_payment_mode_display()),
    ]
    row_height = 8 * mm
    draw_info_table(pdf, 18 * mm, height - 58 * mm, table_width, info_rows, row_height=row_height)
    info_bottom = height - 58 * mm - len(info_rows) * row_height

    parcels = list(delivery.parcels.all())
    if parcels:
        pdf.setFillColor(INNOVEVENT_NAVY)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(18 * mm, info_bottom - 8 * mm, "COLIS")
        parcel_rows = [
            (f"{p.description} × {p.quantity}", f"{p.weight_kg} kg" if p.weight_kg else "—")
            for p in parcels
        ]
        draw_info_table(pdf, 18 * mm, info_bottom - 12 * mm, table_width, parcel_rows, row_height=row_height)
        qr_top = info_bottom - 12 * mm - len(parcel_rows) * row_height - 10 * mm
    else:
        qr_top = info_bottom - 10 * mm

    qr_size = 24 * mm
    qr_y = max(qr_top - qr_size, 28 * mm)
    qr_png = build_qr_png_bytes(sign_payload("delivery", delivery.pk))
    draw_qr_image(pdf, ImageReader(BytesIO(qr_png)), 18 * mm, qr_y, size=qr_size)
    pdf.setFillColor(HexColor("#6F7780"))
    pdf.setFont("Helvetica", 8)
    pdf.drawString(18 * mm + qr_size + 5 * mm, qr_y + qr_size - 9 * mm, "Scannez ce code pour vérifier")
    pdf.drawString(18 * mm + qr_size + 5 * mm, qr_y + qr_size - 13.5 * mm, "l'authenticité de ce bon de livraison.")

    draw_footer(pdf, width, "Ce document est émis via la plateforme InnovEvent.")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
