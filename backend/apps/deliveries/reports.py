import csv
import io

from django.utils import timezone
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm

from apps.documents.pdf_utils import INNOVEVENT_NAVY, draw_footer, draw_header, draw_info_table, new_canvas

CSV_COLUMNS = [
    ("reference", "Référence"),
    ("tracking_code", "Code de suivi"),
    ("status_display", "Statut"),
    ("delivery_type", "Type"),
    ("priority", "Priorité"),
    ("pickup_address", "Départ"),
    ("destination_address", "Destination"),
    ("carrier_name", "Transporteur"),
    ("driver_name", "Chauffeur"),
    ("amount", "Montant"),
    ("scheduled_date", "Date prévue"),
    ("created_at", "Créée le"),
]


def build_deliveries_csv(deliveries) -> str:
    """Export CSV des livraisons filtrées (Phase 2, section 22) — une ligne
    par livraison, colonnes stables pour être ré-importables dans un tableur."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([label for _, label in CSV_COLUMNS])
    for d in deliveries:
        writer.writerow([
            d.reference,
            d.tracking_code,
            d.get_status_display(),
            d.get_delivery_type_display(),
            d.get_priority_display(),
            d.pickup_address,
            d.destination_address,
            d.carrier.name if d.carrier else "",
            d.driver.full_name if d.driver else "",
            str(d.amount),
            d.scheduled_date.isoformat() if d.scheduled_date else "",
            d.created_at.strftime("%Y-%m-%d %H:%M"),
        ])
    return buffer.getvalue()


def build_deliveries_report_pdf(deliveries, *, date_from=None, date_to=None) -> bytes:
    """Rapport transport paginé (Phase 2, section 22) — synthèse + liste
    détaillée, mêmes helpers graphiques que les autres documents (bon de
    livraison, devis, reçus)."""
    pagesize = landscape(A4)
    width, height = pagesize
    buffer, pdf = new_canvas(pagesize)
    table_width = width - 36 * mm

    deliveries = list(deliveries)
    total_amount = sum(d.amount for d in deliveries)
    period = "Toutes périodes"
    if date_from or date_to:
        period = f"Du {date_from or '…'} au {date_to or '…'}"

    def draw_page_header(subtitle):
        draw_header(pdf, width, title="Rapport transport & livraison", subtitle=subtitle, height=height)

    draw_page_header(timezone.now().strftime("%d/%m/%Y %H:%M"))

    summary_rows = [
        ("Période", period),
        ("Nombre de livraisons", str(len(deliveries))),
        ("Montant total", f"{total_amount:,.0f} XAF".replace(",", " ")),
        ("Livrées", str(sum(1 for d in deliveries if d.status == "delivered"))),
        ("Annulées / échouées", str(sum(1 for d in deliveries if d.status in ("cancelled", "failed")))),
    ]
    draw_info_table(pdf, 18 * mm, height - 44 * mm, table_width, summary_rows, row_height=7 * mm)

    columns = [
        ("Référence", 30 * mm), ("Destination", 55 * mm), ("Transporteur", 45 * mm),
        ("Statut", 40 * mm), ("Montant (XAF)", 30 * mm), ("Créée le", 30 * mm),
    ]
    header_y = height - 44 * mm - len(summary_rows) * 7 * mm - 12 * mm
    row_height = 7 * mm
    bottom_margin = 26 * mm

    def draw_table_header(y):
        pdf.setFillColor(INNOVEVENT_NAVY)
        pdf.rect(18 * mm, y - row_height, table_width, row_height, fill=True, stroke=False)
        pdf.setFillColor(HexColor("#FFFFFF"))
        pdf.setFont("Helvetica-Bold", 8.5)
        x = 18 * mm
        for label, col_width in columns:
            pdf.drawString(x + 2 * mm, y - row_height + 2.3 * mm, label)
            x += col_width
        return y - row_height

    y = draw_table_header(header_y)
    pdf.setFont("Helvetica", 8)
    for i, d in enumerate(deliveries):
        if y - row_height < bottom_margin:
            draw_footer(pdf, width, "Ce rapport est généré automatiquement via la plateforme InnovEvent.")
            pdf.showPage()
            draw_page_header(timezone.now().strftime("%d/%m/%Y %H:%M"))
            y = draw_table_header(height - 44 * mm)
            pdf.setFont("Helvetica", 8)
        if i % 2 == 0:
            pdf.setFillColor(HexColor("#FAFBFC"))
            pdf.rect(18 * mm, y - row_height, table_width, row_height, fill=True, stroke=False)
        pdf.setFillColor(HexColor("#323232"))
        values = [
            d.reference, d.destination_address[:38], d.carrier.name if d.carrier else "—",
            d.get_status_display(), f"{d.amount:,.0f}".replace(",", " "), d.created_at.strftime("%d/%m/%Y"),
        ]
        x = 18 * mm
        for value, (_, col_width) in zip(values, columns):
            pdf.drawString(x + 2 * mm, y - row_height + 2.3 * mm, str(value))
            x += col_width
        y -= row_height

    draw_footer(pdf, width, "Ce rapport est généré automatiquement via la plateforme InnovEvent.")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
