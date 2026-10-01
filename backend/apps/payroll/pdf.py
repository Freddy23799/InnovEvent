from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas

from apps.documents.pdf_utils import draw_footer, draw_header


def build_payslip_pdf(payslip) -> bytes:
    width, height = A4
    buffer = BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=A4)

    draw_header(pdf, width, title="Fiche de paie", subtitle=f"{payslip.period_month:02d}/{payslip.period_year}")

    pdf.setFillColor("#323232")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(18 * mm, height - 45 * mm, f"{payslip.employee.first_name} {payslip.employee.last_name}")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(18 * mm, height - 52 * mm, payslip.employee.position)

    rows = [
        ("Salaire de base", payslip.base_salary),
        ("Primes", payslip.bonuses),
        ("Indemnités", payslip.allowances),
        ("Retenues", -payslip.deductions),
    ]
    y = height - 70 * mm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(18 * mm, y, "Libellé")
    pdf.drawRightString(width - 18 * mm, y, "Montant (XAF)")
    y -= 6 * mm
    pdf.setFont("Helvetica", 10)
    for label, amount in rows:
        pdf.drawString(18 * mm, y, label)
        pdf.drawRightString(width - 18 * mm, y, f"{amount:,.0f}".replace(",", " "))
        y -= 7 * mm

    pdf.setFillColor("#C0272D")
    pdf.rect(18 * mm, y - 4 * mm, width - 36 * mm, 12 * mm, fill=True, stroke=False)
    pdf.setFillColor("#FFFFFF")
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(22 * mm, y - 0.5 * mm, "NET À PAYER")
    pdf.drawRightString(width - 22 * mm, y - 0.5 * mm, f"{payslip.net_pay:,.0f} XAF".replace(",", " "))

    draw_footer(pdf, width, "InnovEvent-GS — Fiche de paie générée automatiquement, cachet numérique de l'établissement.")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
