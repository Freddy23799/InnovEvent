from io import BytesIO

from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas

from apps.documents.qr_utils import build_qr_png_bytes
from apps.documents.signing import sign_payload


def build_provider_badge_pdf(provider) -> bytes:
    """Badge d'accès prestataire au format carte, avec QR signé permettant de
    vérifier son identité au contrôle d'entrée (section « fournisseurs »)."""
    card_size = (85.6 * mm, 54 * mm)
    buffer = BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=card_size)
    width, height = card_size

    pdf.setFillColor("#39495b")
    pdf.rect(0, height - 14 * mm, width, 14 * mm, fill=True, stroke=False)
    pdf.setFillColor("#ffffff")
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(4 * mm, height - 9.5 * mm, "InnovEvent — Prestataire")

    pdf.setFillColor("#323232")
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(4 * mm, height - 22 * mm, provider.name)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(4 * mm, height - 28 * mm, f"Catégorie : {provider.get_category_display()}")
    pdf.drawString(4 * mm, height - 33 * mm, f"Pièce d'identité : {provider.identity_number or 'Non renseignée'}")
    pdf.drawString(4 * mm, height - 38 * mm, f"Contact : {provider.contact_phone or provider.contact_email or '—'}")

    qr_png = build_qr_png_bytes(sign_payload("provider-badge", provider.id))
    pdf.drawImage(ImageReader(BytesIO(qr_png)), width - 22 * mm, 4 * mm, width=18 * mm, height=18 * mm, mask="auto")

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
