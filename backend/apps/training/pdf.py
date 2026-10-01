from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas

from apps.documents.pdf_utils import _get_logo, draw_footer, draw_header, draw_qr_image
from apps.documents.qr_utils import build_qr_png_bytes
from apps.documents.signing import sign_payload


def build_certificate_pdf(certificate) -> bytes:
    enrollment = certificate.enrollment
    width, height = A4
    buffer = BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=A4)

    draw_header(pdf, width, title="Attestation de fin de formation", subtitle=enrollment.matricule)

    pdf.setFillColor("#323232")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 70 * mm, "ATTESTATION DE FIN DE FORMATION")

    pdf.setFont("Helvetica", 12)
    participant_name = enrollment.participant.get_full_name() or enrollment.participant.username
    text = (
        f"InnovEvent-GS certifie que {participant_name} (matricule {enrollment.matricule}) "
        f"a suivi avec succès la formation « {enrollment.training.name} »"
        f"{' — ' + enrollment.training.session_label if enrollment.training.session_label else ''}."
    )
    text_object = pdf.beginText(25 * mm, height - 95 * mm)
    text_object.setFont("Helvetica", 12)
    for line in _wrap_text(text, 90):
        text_object.textLine(line)
    pdf.drawText(text_object)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(25 * mm, height - 130 * mm, f"Délivrée le {certificate.issued_at:%d/%m/%Y}")
    if certificate.validated_by:
        pdf.drawString(25 * mm, height - 137 * mm, f"Validée par {certificate.validated_by.get_full_name() or certificate.validated_by.username}")

    qr_png = build_qr_png_bytes(sign_payload("certificate", certificate.id))
    draw_qr_image(pdf, ImageReader(BytesIO(qr_png)), width - 55 * mm, 30 * mm, size=30 * mm)

    draw_footer(pdf, width, "InnovEvent-GS — Document officiel, vérifiable via son QR code.")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _resolve_badge_photo(badge):
    """Cherche une photo pertinente pour le badge : celle prise à l'enrôlement en
    formation en priorité, sinon l'avatar du profil, sinon aucune (silhouette)."""
    from apps.training.models import Enrollment

    if badge.purpose == badge.Purpose.TRAINING:
        enrollment = (
            Enrollment.objects.filter(participant=badge.user)
            .exclude(photo="")
            .order_by("-enrolled_at")
            .first()
        )
        if enrollment and enrollment.photo:
            return enrollment.photo
    if badge.user.avatar:
        return badge.user.avatar
    return None


def build_badge_pdf(badge) -> bytes:
    card_size = (85.6 * mm, 54 * mm)  # format carte bancaire, standard badge
    buffer = BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=card_size)
    width, height = card_size

    # Bande d'en-tête avec logo
    pdf.setFillColor(HexColor("#39495b"))
    pdf.rect(0, height - 13 * mm, width, 13 * mm, fill=True, stroke=False)
    logo = _get_logo()
    text_x = 4 * mm
    if logo:
        logo_size = 9 * mm
        pdf.drawImage(logo, 4 * mm, height - 13 * mm + (13 * mm - logo_size) / 2, width=logo_size, height=logo_size, mask="auto")
        text_x = 4 * mm + logo_size + 2 * mm
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(text_x, height - 9 * mm, "InnovEvent")
    pdf.setFont("Helvetica", 6.5)
    pdf.drawRightString(width - 4 * mm, height - 9 * mm, badge.get_purpose_display().upper())

    # Photo d'identité
    photo_w, photo_h = 18 * mm, 22 * mm
    photo_x, photo_y = 4 * mm, height - 13 * mm - photo_h - 2.5 * mm
    photo_field = _resolve_badge_photo(badge)
    if photo_field:
        try:
            pdf.drawImage(ImageReader(photo_field.path), photo_x, photo_y, width=photo_w, height=photo_h, mask="auto")
        except Exception:
            photo_field = None
    if not photo_field:
        pdf.setFillColor(HexColor("#eef0f2"))
        pdf.rect(photo_x, photo_y, photo_w, photo_h, fill=True, stroke=False)
        pdf.setFillColor(HexColor("#9aa3ac"))
        pdf.setFont("Helvetica", 14)
        pdf.drawCentredString(photo_x + photo_w / 2, photo_y + photo_h / 2 - 3, "?")
    pdf.setStrokeColor(HexColor("#dde1e5"))
    pdf.rect(photo_x, photo_y, photo_w, photo_h, fill=False, stroke=True)

    # Informations
    info_x = photo_x + photo_w + 3 * mm
    pdf.setFillColor(HexColor("#323232"))
    pdf.setFont("Helvetica-Bold", 9.5)
    holder_name = badge.user.get_full_name() or badge.user.username
    pdf.drawString(info_x, height - 18 * mm, holder_name)
    pdf.setFont("Helvetica", 7)
    pdf.setFillColor(HexColor("#6f7780"))
    pdf.drawString(info_x, height - 22.5 * mm, "Matricule")
    pdf.setFillColor(HexColor("#323232"))
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawString(info_x, height - 26 * mm, badge.matricule)
    pdf.setFillColor(HexColor("#6f7780"))
    pdf.setFont("Helvetica", 7)
    pdf.drawString(info_x, height - 30 * mm, "Validité")
    pdf.setFillColor(HexColor("#323232"))
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawString(info_x, height - 33.5 * mm, f"{badge.valid_from:%d/%m/%Y} — {badge.valid_until:%d/%m/%Y}")

    # Bande de statut
    active = badge.is_currently_valid()
    pdf.setFillColor(HexColor("#1E7B4D") if active else HexColor("#C0272D"))
    pdf.rect(0, 0, width, 5 * mm, fill=True, stroke=False)
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.drawCentredString(width / 2 - 8 * mm, 1.5 * mm, "VALIDE" if active else "EXPIRÉ")

    qr_png = build_qr_png_bytes(sign_payload("badge", badge.id))
    draw_qr_image(pdf, ImageReader(BytesIO(qr_png)), width - 20 * mm, 6 * mm, size=16 * mm)

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _wrap_text(text, max_chars):
    words = text.split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 > max_chars:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines
