from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas

from apps.documents.company import LOGO_PATH
from apps.documents.qr_utils import build_qr_png_bytes
from apps.documents.signing import sign_payload

# Même langage visuel que le billet payant (apps/tickets/pdf.py) — une seule
# déclinaison, chaleureuse et formelle, adaptée à une invitation (mariage,
# anniversaire, cérémonie...) plutôt qu'à un billet payant à plusieurs gammes.
IVORY = HexColor("#FAF8F3")
NAVY = HexColor("#1F2D3B")
NAVY_MUTED = HexColor("#7C8894")
STUB_BG = HexColor("#1B2733")
STUB_MUTED = HexColor("#AAB4BE")
RED_ACCENT = HexColor("#B0272D")

TICKET_SIZE = (210 * mm, 100 * mm)
STUB_WIDTH = 64 * mm

_logo_reader = None


def _get_logo():
    global _logo_reader
    if _logo_reader is None:
        try:
            _logo_reader = ImageReader(LOGO_PATH)
        except Exception:
            _logo_reader = False
    return _logo_reader or None


def _truncate(text, max_len):
    text = str(text)
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _tracked(text, gap=" "):
    return gap.join(text)


def build_participant_invitation_pdf(participant) -> bytes:
    """Billet d'invitation à un événement (participant ajouté par un client ou
    un organisateur — section « participants »), avec QR signé réutilisable
    pour un futur contrôle d'accès à l'entrée."""
    event = participant.event
    width, height = TICKET_SIZE
    main_width = width - STUB_WIDTH
    buffer = BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=TICKET_SIZE)

    # --- Corps principal ---
    pdf.setFillColor(IVORY)
    pdf.rect(0, 0, main_width, height, fill=True, stroke=False)
    pdf.saveState()
    pdf.setStrokeColor(NAVY)
    pdf.setLineWidth(0.5)
    pdf.rect(3 * mm, 3 * mm, main_width - 6 * mm, height - 6 * mm, fill=False, stroke=True)
    pdf.restoreState()

    margin = 10 * mm
    logo = _get_logo()
    text_x = margin
    if logo:
        logo_size = 8 * mm
        pdf.drawImage(logo, margin, height - 20 * mm, width=logo_size, height=logo_size, mask="auto")
        text_x = margin + logo_size + 3.5 * mm
    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 10.5)
    pdf.drawString(text_x, height - 14 * mm, "INNOVEVENT")
    pdf.setFillColor(NAVY_MUTED)
    pdf.setFont("Helvetica", 6.5)
    pdf.drawString(text_x, height - 19 * mm, _tracked("GROUP"))

    pdf.setFillColor(RED_ACCENT)
    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.drawRightString(main_width - margin, height - 17.5 * mm, _tracked("INVITATION"))

    pdf.setStrokeColor(RED_ACCENT)
    pdf.setLineWidth(0.5)
    pdf.line(margin, height - 24 * mm, main_width - margin, height - 24 * mm)

    pdf.setFillColor(NAVY)
    pdf.setFont("Times-Bold", 27)
    pdf.drawString(margin, height - 40 * mm, _truncate(event.title, 32))

    pdf.setFont("Helvetica", 9.5)
    pdf.setFillColor(NAVY_MUTED)
    pdf.drawString(margin, height - 47 * mm, f"{event.start_date:%d/%m/%Y à %H:%M}")
    if event.venue_id:
        pdf.drawString(margin, height - 53 * mm, _truncate(event.venue.name, 42))

    divider_y = height - 60 * mm
    pdf.setStrokeColor(RED_ACCENT)
    pdf.setLineWidth(0.35)
    pdf.line(margin, divider_y, main_width - margin, divider_y)

    row_y = divider_y - 10 * mm
    organizer_name = event.organizer.get_full_name() or event.organizer.username
    guest_name = participant.full_name or (participant.user.get_full_name() if participant.user else "Invité(e)")
    for label, value, x, max_chars in [
        ("INVITÉ(E)", guest_name, margin, 26),
        ("ORGANISÉ PAR", organizer_name, margin + 82 * mm, 24),
    ]:
        pdf.setFont("Helvetica-Bold", 7.5)
        pdf.setFillColor(RED_ACCENT)
        pdf.drawString(x, row_y, label)
        pdf.setFont("Helvetica", 10.5)
        pdf.setFillColor(NAVY)
        pdf.drawString(x, row_y - 5.5 * mm, _truncate(str(value), max_chars))

    pdf.setFont("Helvetica-Oblique", 6.5)
    pdf.setFillColor(NAVY_MUTED)
    pdf.drawString(margin, 8 * mm, "Invitation personnelle — présentez le QR code du talon à l'entrée.")

    # --- Talon ---
    pdf.saveState()
    pdf.setStrokeColor(NAVY)
    pdf.setDash(1.6, 2.4)
    pdf.setLineWidth(0.9)
    pdf.line(main_width, 8 * mm, main_width, height - 8 * mm)
    pdf.restoreState()
    pdf.setFillColor(IVORY)
    pdf.circle(main_width, height, 4.4 * mm, fill=True, stroke=False)
    pdf.circle(main_width, 0, 4.4 * mm, fill=True, stroke=False)

    pdf.setFillColor(STUB_BG)
    pdf.rect(main_width, 0, STUB_WIDTH, height, fill=True, stroke=False)
    pdf.saveState()
    pdf.setStrokeColor(RED_ACCENT)
    pdf.setLineWidth(0.5)
    pdf.rect(main_width + 3 * mm, 3 * mm, STUB_WIDTH - 6 * mm, height - 6 * mm, fill=False, stroke=True)
    pdf.restoreState()

    stub_center = main_width + STUB_WIDTH / 2
    pdf.setFillColor(RED_ACCENT)
    pdf.setFont("Helvetica-Bold", 6.3)
    pdf.drawCentredString(stub_center, height - 14 * mm, _tracked("ACCÈS"))

    token = sign_payload("event-participant", participant.id)
    qr_png = build_qr_png_bytes(token)
    qr_size = 36 * mm
    qr_x = stub_center - qr_size / 2
    qr_y = height - qr_size - 22 * mm
    pdf.setFillColor(HexColor("#FFFFFF"))
    pdf.roundRect(qr_x - 3 * mm, qr_y - 3 * mm, qr_size + 6 * mm, qr_size + 6 * mm, 2, fill=True, stroke=False)
    pdf.drawImage(ImageReader(BytesIO(qr_png)), qr_x, qr_y, width=qr_size, height=qr_size, mask="auto")

    pdf.setFont("Helvetica", 6)
    pdf.setFillColor(STUB_MUTED)
    pdf.drawCentredString(stub_center, qr_y - 8 * mm, _tracked("PRÉSENTEZ CE QR À L'ENTRÉE"))
    pdf.setFillColor(RED_ACCENT)
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawCentredString(stub_center, qr_y - 14 * mm, f"RÉF. {participant.id:06d}")

    pdf.setFillColor(RED_ACCENT)
    pdf.roundRect(main_width + 10 * mm, 9 * mm, STUB_WIDTH - 20 * mm, 8 * mm, 4, fill=True, stroke=False)
    pdf.setFillColor(HexColor("#FFFFFF"))
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawCentredString(stub_center, 11.5 * mm, _tracked("INVITÉ(E)"))

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
