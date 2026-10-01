from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas

from apps.documents.company import LOGO_PATH

from .models import Ticket
from .qr import build_qr_png_bytes, sign_ticket_code

# --- Palette « billetterie haut de gamme » -----------------------------------
# Premium : noir profond + doré champagne + blanc cassé (nocturne, prestige).
PREMIUM_BG = HexColor("#0B0B0D")
PREMIUM_PANEL = HexColor("#141416")
GOLD = HexColor("#C6A662")
GOLD_LIGHT = HexColor("#E4D3A6")
GOLD_MUTED = HexColor("#8C744A")
IVORY = HexColor("#F5F1E7")

# Standard : ivoire + bleu nuit + argent, accent rouge InnovEvent (éditorial, élégant).
STANDARD_BG = HexColor("#FAF8F3")
STANDARD_STUB = HexColor("#1B2733")
NAVY = HexColor("#1F2D3B")
NAVY_MUTED = HexColor("#7C8894")
SILVER = HexColor("#AEB4BC")
RED_ACCENT = HexColor("#B0272D")

# Teintes pré-mélangées (plutôt que de la transparence PDF réelle, peu fiable
# selon les moteurs de rendu/impression) pour les détails discrets sur fond sombre.
PREMIUM_PATTERN = HexColor("#3A3226")
PREMIUM_STUB_MUTED = HexColor("#B6AD98")
STANDARD_PATTERN = HexColor("#3D2A2C")
STANDARD_STUB_MUTED = HexColor("#AAB4BE")

# Format « billet à souche » à l'italienne, proche d'un vrai billet imprimé —
# davantage d'espace négatif que la version précédente (section « composition »).
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
    """Simule un espacement de lettres (letter-tracking) pour les libellés et
    surtitres en petites capitales — absent de la simple API drawString."""
    return gap.join(text)


def _emboss_text(pdf, x, y, text, font, size, color, shadow):
    """Léger effet d'estampage : un double filet décalé, très proche du texte
    principal, pour suggérer un relief sans surcharger le rendu."""
    pdf.setFont(font, size)
    pdf.setFillColor(shadow)
    pdf.drawString(x + 0.28 * mm, y - 0.28 * mm, text)
    pdf.setFillColor(color)
    pdf.drawString(x, y, text)


def _guilloche(pdf, cx, cy, color, rings=4, start_r=5.5 * mm, step=1.6 * mm):
    """Motif de cercles concentriques très fins, discret clin d'œil aux
    éléments de sécurité gravés des billets/certificats haut de gamme.
    `color` doit déjà être la teinte finale voulue (pas de transparence PDF :
    peu fiable selon les moteurs de rendu/impression, voir build_ticket_pdf)."""
    pdf.saveState()
    pdf.setStrokeColor(color)
    pdf.setLineWidth(0.25)
    for i in range(rings):
        pdf.circle(cx, cy, start_r + i * step, fill=0, stroke=1)
    pdf.restoreState()


def _micro_pattern(pdf, x, y, w, h, color):
    """Bande décorative fine (hachures à 45°) très discrète — confinée à une
    zone étroite (clip) pour ne jamais nuire à la lisibilité ni à la sobriété."""
    pdf.saveState()
    path = pdf.beginPath()
    path.rect(x, y, w, h)
    pdf.clipPath(path, stroke=0, fill=0)
    pdf.setStrokeColor(color)
    pdf.setLineWidth(0.25)
    step = 2.4 * mm
    diag = ((w**2 + h**2) ** 0.5) + h
    n = int(diag / step) + 2
    for i in range(-n, n):
        offset = i * step
        pdf.line(x + offset, y, x + offset + h, y + h)
    pdf.restoreState()


def _hairline(pdf, x1, y, x2, color, width=0.5):
    pdf.saveState()
    pdf.setStrokeColor(color)
    pdf.setLineWidth(width)
    pdf.line(x1, y, x2, y)
    pdf.restoreState()


def _draw_perforation(pdf, x, height, dash_color, notch_color):
    pdf.saveState()
    pdf.setStrokeColor(dash_color)
    pdf.setDash(1.6, 2.4)
    pdf.setLineWidth(0.9)
    pdf.line(x, 8 * mm, x, height - 8 * mm)
    pdf.restoreState()
    pdf.setFillColor(notch_color)
    pdf.circle(x, height, 4.4 * mm, fill=True, stroke=False)
    pdf.circle(x, 0, 4.4 * mm, fill=True, stroke=False)


def build_ticket_pdf(ticket) -> bytes:
    """Génère le visuel du billet — deux univers selon `ticket_type.is_premium` :

    - Premium : fond noir profond, typographie éditoriale (serif) dorée sur
      blanc cassé, filets fins, motif guilloché discret — esthétique billet
      VIP / certificat de collection.
    - Standard : fond ivoire, bleu nuit et argent, accent rouge InnovEvent —
      même grille éditoriale, univers plus clair et sobre.
    """
    ticket_type = ticket.ticket_type
    event = ticket_type.event
    premium = ticket_type.is_premium

    width, height = TICKET_SIZE
    main_width = width - STUB_WIDTH
    buffer = BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=TICKET_SIZE)

    if premium:
        bg, panel, accent, accent_light = PREMIUM_BG, PREMIUM_PANEL, GOLD, GOLD_LIGHT
        ink, muted, shadow = IVORY, GOLD_MUTED, HexColor("#000000")
        stub_bg = HexColor("#08080A")
        pattern_color, stub_muted = PREMIUM_PATTERN, PREMIUM_STUB_MUTED
        stub_accent, stub_accent_ink = GOLD, HexColor("#1A1608")
        eyebrow = "BILLET PREMIUM"
    else:
        bg, panel, accent, accent_light = STANDARD_BG, STANDARD_BG, NAVY, RED_ACCENT
        ink, muted, shadow = NAVY, NAVY_MUTED, HexColor("#FFFFFF")
        stub_bg = STANDARD_STUB
        pattern_color, stub_muted = STANDARD_PATTERN, STANDARD_STUB_MUTED
        # Le bleu nuit de l'accent principal se fond dans le talon (également bleu
        # nuit) : on y utilise le rouge InnovEvent, qui garde un contraste net.
        stub_accent, stub_accent_ink = RED_ACCENT, HexColor("#FFFFFF")
        eyebrow = "BILLET D'ENTRÉE OFFICIEL"

    # --- Fond + cadre éditorial -------------------------------------------------
    pdf.setFillColor(bg)
    pdf.rect(0, 0, main_width, height, fill=True, stroke=False)
    pdf.saveState()
    pdf.setStrokeColor(accent)
    pdf.setLineWidth(0.5)
    pdf.rect(3 * mm, 3 * mm, main_width - 6 * mm, height - 6 * mm, fill=False, stroke=True)
    pdf.restoreState()

    margin = 10 * mm

    # Masthead : logo + marque, filet fin sous l'ensemble.
    logo = _get_logo()
    text_x = margin
    if logo:
        logo_size = 8 * mm
        pdf.drawImage(logo, margin, height - 20 * mm, width=logo_size, height=logo_size, mask="auto")
        text_x = margin + logo_size + 3.5 * mm
    pdf.setFont("Helvetica-Bold", 10.5)
    pdf.setFillColor(ink)
    pdf.drawString(text_x, height - 16.2 * mm, "INNOVEVENT")
    pdf.setFont("Helvetica", 6.5)
    pdf.setFillColor(muted)
    pdf.drawString(text_x, height - 19.6 * mm, _tracked("GROUP"))

    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.setFillColor(accent)
    pdf.drawRightString(main_width - margin, height - 17.5 * mm, _tracked(eyebrow))

    _hairline(pdf, margin, height - 24 * mm, main_width - margin, accent, width=0.5)

    # Catégorie (petites capitales espacées) + titre éditorial.
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.setFillColor(accent)
    pdf.drawString(margin, height - 32 * mm, _tracked(_truncate(ticket_type.name.upper(), 28)))

    _emboss_text(pdf, margin, height - 46 * mm, _truncate(event.title, 30), "Times-Bold", 27, ink, shadow)

    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(muted)
    date_line = f"{event.start_date:%d/%m/%Y}  ·  {event.start_date:%H:%M}"
    pdf.drawString(margin, height - 55 * mm, date_line)
    if event.venue_id:
        pdf.drawString(margin, height - 61 * mm, _truncate(event.venue.name, 42))

    _hairline(pdf, margin, height - 68 * mm, main_width - margin, accent, width=0.35)

    # Grille d'informations (éditoriale, 3 colonnes, libellés espacés).
    col_x = [margin, margin + 46 * mm, margin + 92 * mm]
    label_y = height - 76 * mm
    value_y = label_y - 6.2 * mm
    for label, value, x in [
        ("TITULAIRE", ticket.owner.get_full_name() or ticket.owner.username, col_x[0]),
        ("DATE", f"{event.start_date:%d/%m/%Y}", col_x[1]),
        ("TARIF", f"{ticket_type.price} {ticket_type.currency}", col_x[2]),
    ]:
        pdf.setFont("Helvetica-Bold", 6.3)
        pdf.setFillColor(accent)
        pdf.drawString(x, label_y, _tracked(label))
        pdf.setFont("Helvetica", 10.5)
        pdf.setFillColor(ink)
        pdf.drawString(x, value_y, _truncate(str(value), 20))

    # Bande décorative discrète, confinée près de la perforation.
    _micro_pattern(pdf, main_width - 16 * mm, 10 * mm, 6 * mm, height - 20 * mm, pattern_color)

    # Mention légale, pied de page.
    pdf.setFont("Helvetica-Oblique", 6)
    pdf.setFillColor(muted)
    pdf.drawString(margin, 8 * mm, "Billet personnel et non cessible — présentez le QR code du talon à l'entrée.")

    # --- Talon (souche) ----------------------------------------------------
    _draw_perforation(pdf, main_width, height, accent, bg)

    pdf.setFillColor(stub_bg)
    pdf.rect(main_width, 0, STUB_WIDTH, height, fill=True, stroke=False)
    pdf.saveState()
    pdf.setStrokeColor(stub_accent)
    pdf.setLineWidth(0.5)
    pdf.rect(main_width + 3 * mm, 3 * mm, STUB_WIDTH - 6 * mm, height - 6 * mm, fill=False, stroke=True)
    pdf.restoreState()

    stub_center = main_width + STUB_WIDTH / 2
    pdf.setFont("Helvetica-Bold", 6.3)
    pdf.setFillColor(stub_accent)
    pdf.drawCentredString(stub_center, height - 14 * mm, _tracked("ACCÈS"))

    qr_png = build_qr_png_bytes(sign_ticket_code(ticket.code))
    qr_size = 36 * mm
    qr_x = stub_center - qr_size / 2
    qr_y = height - qr_size - 22 * mm
    pdf.setFillColor(IVORY if premium else HexColor("#FFFFFF"))
    pdf.roundRect(qr_x - 3 * mm, qr_y - 3 * mm, qr_size + 6 * mm, qr_size + 6 * mm, 2, fill=True, stroke=False)
    pdf.drawImage(ImageReader(BytesIO(qr_png)), qr_x, qr_y, width=qr_size, height=qr_size, mask="auto")

    pdf.setFont("Helvetica", 6)
    pdf.setFillColor(stub_muted)
    pdf.drawCentredString(stub_center, qr_y - 8 * mm, _tracked("SCANNEZ À L'ENTRÉE"))

    # Numéro de série façon certificat, sur fond guilloché discret.
    serial_y = qr_y - 20 * mm
    _guilloche(pdf, stub_center, serial_y + 1 * mm, pattern_color, rings=3, start_r=9 * mm, step=2.4 * mm)
    pdf.setFillColor(stub_bg)
    pdf.roundRect(stub_center - 21 * mm, serial_y - 3 * mm, 42 * mm, 7 * mm, 3.5, fill=True, stroke=False)
    pdf.setStrokeColor(stub_accent)
    pdf.setLineWidth(0.4)
    pdf.roundRect(stub_center - 21 * mm, serial_y - 3 * mm, 42 * mm, 7 * mm, 3.5, fill=False, stroke=True)
    pdf.setFont("Courier-Bold", 7.5)
    pdf.setFillColor(accent_light if premium else IVORY)
    pdf.drawCentredString(stub_center, serial_y - 0.8 * mm, f"N° {str(ticket.code)[:8].upper()}")

    status_label = ticket.get_status_display().upper()
    is_valid = ticket.status == Ticket.Status.VALID
    badge_color = stub_accent if is_valid else HexColor("#5A6672")
    pdf.setFillColor(badge_color)
    pdf.roundRect(main_width + 10 * mm, 9 * mm, STUB_WIDTH - 20 * mm, 8 * mm, 4, fill=True, stroke=False)
    pdf.setFillColor(stub_accent_ink if is_valid else HexColor("#FFFFFF"))
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawCentredString(stub_center, 11.5 * mm, _tracked(status_label))

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
