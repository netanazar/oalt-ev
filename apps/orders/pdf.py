from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus

from django.conf import settings
from django.urls import reverse
from apps.core.document_verification import invoice_signature
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas


def _fmt_money(value: Decimal | int | float) -> str:
    amount = Decimal(value or 0).quantize(Decimal("0.01"))
    return f"INR {amount:,.2f}"


def _logo_path() -> Path | None:
    candidate = Path(settings.MEDIA_ROOT) / "logo.png"
    return candidate if candidate.exists() else None


def _draw_logo(pdf: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    logo = _logo_path()
    if not logo:
        return
    pdf.drawImage(str(logo), x, y, width=w, height=h, preserveAspectRatio=True, mask="auto")


def _signature_path() -> Path | None:
    candidates = [
        Path(settings.MEDIA_ROOT) / "digital-signature.png",
        Path(settings.MEDIA_ROOT) / "digital_signature.png",
        Path(settings.MEDIA_ROOT) / "signature.png",
        Path(settings.MEDIA_ROOT) / "authorized-signature.png",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _draw_signature(pdf: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    sign = _signature_path()
    if sign:
        pdf.drawImage(str(sign), x, y, width=w, height=h, preserveAspectRatio=True, mask="auto")
        return
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Oblique", 11)
    pdf.drawString(x + 1 * mm, y + (h / 2), "/s/ OALT EV")


def _draw_qr(pdf: canvas.Canvas, payload: str, x: float, y: float, size: float) -> None:
    qr_widget = QrCodeWidget(payload)
    bounds = qr_widget.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    drawing = Drawing(size, size, transform=[size / width, 0, 0, size / height, 0, 0])
    drawing.add(qr_widget)
    renderPDF.draw(drawing, pdf, x, y)


def _build_invoice_qr_payload(order, generated_at) -> str:
    issued_ts = int(generated_at.timestamp())
    signature_hash = invoice_signature(order.order_number, order.total_amount, issued_ts)
    verify_url = (
        f"{settings.SITE_BASE_URL.rstrip('/')}{reverse('core:verify_document')}"
        f"?type=invoice&ref={quote_plus(order.order_number)}&ts={issued_ts}&sig={signature_hash}"
    )
    return verify_url


def build_invoice_pdf(order, generated_at) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    page_w, page_h = A4

    # Header strip
    pdf.setFillColor(colors.HexColor("#C02222"))
    pdf.rect(0, page_h - 55 * mm, page_w, 55 * mm, fill=1, stroke=0)

    # Logo block
    pdf.setFillColor(colors.white)
    pdf.roundRect(15 * mm, page_h - 44 * mm, 36 * mm, 26 * mm, 4 * mm, fill=1, stroke=0)
    _draw_logo(pdf, 17 * mm, page_h - 42 * mm, 32 * mm, 22 * mm)

    # Company details
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(56 * mm, page_h - 24 * mm, "Oalt EV Technology Pvt. Ltd.")
    pdf.setFont("Helvetica", 9.5)
    pdf.drawString(56 * mm, page_h - 30 * mm, "643/1 First Floor, Mundka More, New Delhi - 110041")
    pdf.drawString(56 * mm, page_h - 35 * mm, "support@oaltev.com  |  +91 7291880088")

    # Invoice meta
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawRightString(page_w - 15 * mm, page_h - 22 * mm, "TAX INVOICE")
    pdf.setFont("Helvetica", 9.5)
    pdf.drawRightString(page_w - 15 * mm, page_h - 28 * mm, f"Invoice: INV-{order.order_number}")
    pdf.drawRightString(page_w - 15 * mm, page_h - 33 * mm, f"Order: {order.order_number}")
    pdf.drawRightString(page_w - 15 * mm, page_h - 38 * mm, f"Generated: {generated_at:%d %b %Y, %I:%M %p}")

    y = page_h - 67 * mm

    # Billing / order summary cards
    pdf.setFillColor(colors.HexColor("#F8FAFC"))
    pdf.setStrokeColor(colors.HexColor("#E2E8F0"))
    pdf.roundRect(15 * mm, y - 30 * mm, 85 * mm, 30 * mm, 3 * mm, fill=1, stroke=1)
    pdf.roundRect(107 * mm, y - 30 * mm, 88 * mm, 30 * mm, 3 * mm, fill=1, stroke=1)

    addr = getattr(order, "shipping_address", None)
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(18 * mm, y - 6 * mm, "Billed To")
    pdf.setFont("Helvetica", 9)
    if addr:
        billing_lines = [
            addr.full_name,
            f"{addr.address_line1}{', ' + addr.address_line2 if addr.address_line2 else ''}",
            f"{addr.city}, {addr.state} - {addr.postal_code}",
            f"Phone: {addr.phone}",
            f"Email: {addr.email}",
        ]
        if addr.gst_number:
            billing_lines.append(f"GSTIN: {addr.gst_number}")
    else:
        billing_lines = ["Address not available"]
    line_y = y - 11 * mm
    for line in billing_lines[:6]:
        pdf.drawString(18 * mm, line_y, line[:58])
        line_y -= 4.2 * mm

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(110 * mm, y - 6 * mm, "Order Summary")
    pdf.setFont("Helvetica", 9)
    summary_lines = [
        f"Payment: {order.get_payment_method_display()}",
        f"Status: {order.get_status_display()}",
        f"Order Date: {order.created_at:%d %b %Y}",
        f"Delivered/Updated: {order.updated_at:%d %b %Y}",
    ]
    line_y = y - 11 * mm
    for line in summary_lines:
        pdf.drawString(110 * mm, line_y, line)
        line_y -= 4.2 * mm

    y -= 38 * mm

    # Table header
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.rect(15 * mm, y - 8 * mm, 180 * mm, 8 * mm, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 9.5)
    pdf.drawString(18 * mm, y - 5.5 * mm, "Item")
    pdf.drawRightString(130 * mm, y - 5.5 * mm, "Qty")
    pdf.drawRightString(162 * mm, y - 5.5 * mm, "Unit Price")
    pdf.drawRightString(192 * mm, y - 5.5 * mm, "Line Total")
    y -= 8 * mm

    row_h = 10 * mm
    pdf.setFont("Helvetica", 9)
    pdf.setStrokeColor(colors.HexColor("#E2E8F0"))

    for item in order.items.all():
        name_lines = simpleSplit(item.product.name, "Helvetica", 9, 95 * mm)
        needed_h = max(row_h, (len(name_lines) * 4.2 * mm) + 4 * mm)
        if y - needed_h < 82 * mm:
            pdf.showPage()
            page_w, page_h = A4
            y = page_h - 20 * mm
            pdf.setFillColor(colors.HexColor("#0F172A"))
            pdf.rect(15 * mm, y - 8 * mm, 180 * mm, 8 * mm, fill=1, stroke=0)
            pdf.setFillColor(colors.white)
            pdf.setFont("Helvetica-Bold", 9.5)
            pdf.drawString(18 * mm, y - 5.5 * mm, "Item")
            pdf.drawRightString(130 * mm, y - 5.5 * mm, "Qty")
            pdf.drawRightString(162 * mm, y - 5.5 * mm, "Unit Price")
            pdf.drawRightString(192 * mm, y - 5.5 * mm, "Line Total")
            y -= 8 * mm
            pdf.setFont("Helvetica", 9)

        pdf.setFillColor(colors.white)
        pdf.rect(15 * mm, y - needed_h, 180 * mm, needed_h, fill=1, stroke=1)
        pdf.setFillColor(colors.HexColor("#111827"))

        text_y = y - 4.2 * mm
        for line in name_lines:
            pdf.drawString(18 * mm, text_y, line)
            text_y -= 4.2 * mm

        pdf.drawRightString(130 * mm, y - 5.5 * mm, str(item.quantity))
        pdf.drawRightString(162 * mm, y - 5.5 * mm, _fmt_money(item.price))
        pdf.drawRightString(192 * mm, y - 5.5 * mm, _fmt_money(item.line_total))
        y -= needed_h

    # Totals box
    y -= 4 * mm
    totals_w = 75 * mm
    box_x = page_w - 15 * mm - totals_w
    box_h = 30 * mm
    pdf.setFillColor(colors.HexColor("#F8FAFC"))
    pdf.roundRect(box_x, y - box_h, totals_w, box_h, 2 * mm, fill=1, stroke=1)
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica", 9)
    pdf.drawString(box_x + 4 * mm, y - 6 * mm, "Subtotal")
    pdf.drawRightString(box_x + totals_w - 4 * mm, y - 6 * mm, _fmt_money(order.subtotal))
    pdf.drawString(box_x + 4 * mm, y - 11 * mm, "Discount")
    pdf.drawRightString(box_x + totals_w - 4 * mm, y - 11 * mm, f"- {_fmt_money(order.discount)}")
    pdf.drawString(box_x + 4 * mm, y - 16 * mm, "GST")
    pdf.drawRightString(box_x + totals_w - 4 * mm, y - 16 * mm, _fmt_money(order.gst))
    pdf.setStrokeColor(colors.HexColor("#CBD5E1"))
    pdf.line(box_x + 3 * mm, y - 19 * mm, box_x + totals_w - 3 * mm, y - 19 * mm)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(box_x + 4 * mm, y - 25 * mm, "Total Paid")
    pdf.drawRightString(box_x + totals_w - 4 * mm, y - 25 * mm, _fmt_money(order.total_amount))

    # Verification & digital signature block
    qr_payload = _build_invoice_qr_payload(order, generated_at)
    issued_ts = int(generated_at.timestamp())
    signature_hash = invoice_signature(order.order_number, order.total_amount, issued_ts)

    block_y = 20 * mm
    block_h = 42 * mm
    block_x = 15 * mm
    block_w = page_w - 30 * mm
    pdf.setFillColor(colors.HexColor("#FFFFFF"))
    pdf.setStrokeColor(colors.HexColor("#E2E8F0"))
    pdf.roundRect(block_x, block_y, block_w, block_h, 2.2 * mm, fill=1, stroke=1)

    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(block_x + 4 * mm, block_y + block_h - 6 * mm, "QR Verification")
    pdf.setFont("Helvetica", 8.8)
    pdf.setFillColor(colors.HexColor("#475569"))
    pdf.drawString(block_x + 4 * mm, block_y + block_h - 11 * mm, "Scan to verify invoice details on Oalt EV portal.")

    _draw_qr(pdf, qr_payload, block_x + 4 * mm, block_y + 4 * mm, 26 * mm)

    sign_x = block_x + 38 * mm
    sign_y = block_y + 7 * mm
    sign_w = 58 * mm
    sign_h = 16 * mm
    pdf.setStrokeColor(colors.HexColor("#CBD5E1"))
    pdf.line(sign_x, sign_y + 1 * mm, sign_x + sign_w, sign_y + 1 * mm)
    _draw_signature(pdf, sign_x + 2 * mm, sign_y + 2 * mm, sign_w - 4 * mm, sign_h - 3 * mm)
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(sign_x, block_y + block_h - 6 * mm, "Digital Signature")
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(colors.HexColor("#475569"))
    pdf.drawString(sign_x, block_y + 2.8 * mm, "Authorized Signatory, Oalt EV Technology Pvt. Ltd.")

    hash_x = sign_x + 66 * mm
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(hash_x, block_y + block_h - 6 * mm, "Document Hash")
    pdf.setFont("Helvetica", 8.8)
    pdf.setFillColor(colors.HexColor("#475569"))
    pdf.drawString(hash_x, block_y + block_h - 11 * mm, signature_hash)
    pdf.drawString(hash_x, block_y + block_h - 16 * mm, "Use this hash for support-side verification.")
    verify_url = (
        f"{settings.SITE_BASE_URL.rstrip('/')}{reverse('core:verify_document')}"
        f"?type=invoice&ref={quote_plus(order.order_number)}&ts={issued_ts}&sig={signature_hash}"
    )
    pdf.setFont("Helvetica", 7.6)
    pdf.drawString(hash_x, block_y + 4.5 * mm, "Verify URL:")
    pdf.drawString(hash_x, block_y + 1.5 * mm, verify_url[:60])
    if len(verify_url) > 60:
        pdf.drawString(hash_x, block_y - 1.5 * mm, verify_url[60:120])

    # Footer
    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.setFont("Helvetica", 8.5)
    pdf.drawString(
        15 * mm,
        14 * mm,
        "System generated invoice. For support contact support@oaltev.com | +91 7291880088",
    )

    pdf.showPage()
    pdf.save()
    data = buffer.getvalue()
    buffer.close()
    return data
