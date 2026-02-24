from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus
from datetime import timedelta, date

from django.conf import settings
from django.urls import reverse

from apps.core.document_verification import warranty_signature
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas


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
    pdf.setFillColor(colors.HexColor("#111827"))
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


def _draw_wrapped_lines(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    font_name: str,
    font_size: float,
    line_step: float,
    max_lines: int,
) -> float:
    lines = simpleSplit(str(text or "-"), font_name, font_size, width)
    pdf.setFont(font_name, font_size)
    current_y = y
    for line in lines[:max_lines]:
        pdf.drawString(x, current_y, line)
        current_y -= line_step
    return current_y


def _safe_add_years(start_date: date, years: int) -> date:
    try:
        return start_date.replace(year=start_date.year + years)
    except ValueError:
        return start_date.replace(month=2, day=28, year=start_date.year + years)


def _product_image_path(claim) -> Path | None:
    first_item = claim.order.items.select_related("product").first()
    if not first_item or not getattr(first_item.product, "main_image", None):
        return None
    try:
        path = Path(first_item.product.main_image.path)
    except Exception:
        return None
    return path if path.exists() else None


def _build_warranty_verify_url(claim, generated_at):
    issued_ts = int(generated_at.timestamp())
    sig = warranty_signature(claim.claim_number, claim.warranty_card_number, claim.order.order_number, issued_ts)
    verify_url = (
        f"{settings.SITE_BASE_URL.rstrip('/')}{reverse('core:verify_document')}"
        f"?type=warranty&ref={quote_plus(claim.claim_number)}"
        f"&order={quote_plus(claim.order.order_number)}"
        f"&card={quote_plus(claim.warranty_card_number)}"
        f"&ts={issued_ts}&sig={sig}"
    )
    return verify_url, sig


def build_warranty_card_pdf(claim, generated_at) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    page_w, page_h = landscape(A4)

    # Premium background
    pdf.setFillColor(colors.HexColor("#0A0F1D"))
    pdf.rect(0, 0, page_w, page_h, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#C02222"))
    pdf.rect(0, page_h - 7 * mm, page_w, 7 * mm, fill=1, stroke=0)

    # Main certificate card
    card_x = 14 * mm
    card_y = 14 * mm
    card_w = page_w - 28 * mm
    card_h = page_h - 28 * mm
    pdf.setFillColor(colors.HexColor("#FFFFFF"))
    pdf.roundRect(card_x, card_y, card_w, card_h, 5 * mm, fill=1, stroke=0)

    # Left premium panel (reference-inspired)
    left_w = 86 * mm
    pdf.setFillColor(colors.HexColor("#1E293B"))
    pdf.roundRect(card_x, card_y, left_w, card_h, 5 * mm, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#0EA5E9"))
    pdf.circle(card_x + 6 * mm, card_y + card_h - 8 * mm, 32 * mm, fill=0, stroke=1)
    pdf.setFillColor(colors.HexColor("#C02222"))
    pdf.circle(card_x + 6 * mm, card_y + card_h - 8 * mm, 27 * mm, fill=0, stroke=1)

    # Logo box
    pdf.setFillColor(colors.white)
    pdf.roundRect(card_x + 8 * mm, card_y + card_h - 28 * mm, left_w - 16 * mm, 18 * mm, 3 * mm, fill=1, stroke=0)
    _draw_logo(pdf, card_x + 10 * mm, card_y + card_h - 26 * mm, left_w - 20 * mm, 14 * mm)

    # Title
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(card_x + 9 * mm, card_y + card_h - 36 * mm, "Premium Warranty")
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(card_x + 9 * mm, card_y + card_h - 45 * mm, "CERTIFICATE")
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.HexColor("#CBD5E1"))
    pdf.drawString(card_x + 9 * mm, card_y + card_h - 50 * mm, "Issued by Oalt EV Technology Pvt. Ltd.")

    # Product image block
    product_img = _product_image_path(claim)
    product_box_y = card_y + card_h - 95 * mm
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.roundRect(card_x + 8 * mm, product_box_y, left_w - 16 * mm, 36 * mm, 3 * mm, fill=1, stroke=0)
    if product_img:
        pdf.drawImage(
            str(product_img),
            card_x + 10 * mm,
            product_box_y + 2 * mm,
            width=left_w - 20 * mm,
            height=32 * mm,
            preserveAspectRatio=True,
            mask="auto",
        )
    else:
        pdf.setFillColor(colors.HexColor("#E2E8F0"))
        pdf.setFont("Helvetica", 9)
        pdf.drawCentredString(card_x + left_w / 2, product_box_y + 17 * mm, "Product image not available")

    # QR and hash panel (left bottom)
    verify_url, signature_hash = _build_warranty_verify_url(claim, generated_at)
    qr_size = 24 * mm
    qr_x = card_x + 10 * mm
    qr_y = card_y + 14 * mm
    pdf.setFillColor(colors.white)
    pdf.roundRect(qr_x - 2 * mm, qr_y - 2 * mm, qr_size + 4 * mm, qr_size + 4 * mm, 2 * mm, fill=1, stroke=0)
    _draw_qr(pdf, verify_url, qr_x, qr_y, qr_size)
    pdf.setFillColor(colors.HexColor("#E2E8F0"))
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(qr_x + qr_size + 5 * mm, qr_y + 18 * mm, "Verify Warranty")
    pdf.setFont("Helvetica", 7.2)
    pdf.drawString(qr_x + qr_size + 5 * mm, qr_y + 13 * mm, "Scan QR to validate")
    pdf.drawString(qr_x + qr_size + 5 * mm, qr_y + 9 * mm, "claim authenticity")
    pdf.drawString(qr_x + qr_size + 5 * mm, qr_y + 4 * mm, f"Hash: {signature_hash[:12]}...")

    # Right content panel
    right_x = card_x + left_w + 8 * mm
    right_w = card_w - left_w - 16 * mm
    top_y = card_y + card_h - 12 * mm
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(right_x, top_y, "OALT WARRANTY CARD")
    pdf.setFillColor(colors.HexColor("#475569"))
    pdf.setFont("Helvetica", 10)
    pdf.drawString(right_x, top_y - 6 * mm, "Retain this document for support and service eligibility.")

    # Status badge
    status_text = claim.get_status_display()
    badge_w = max(34 * mm, min(54 * mm, (len(status_text) + 8) * 2.3 * mm))
    pdf.setFillColor(colors.HexColor("#C02222"))
    pdf.roundRect(right_x + right_w - badge_w, top_y - 3 * mm, badge_w, 9 * mm, 2.5 * mm, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawCentredString(right_x + right_w - (badge_w / 2), top_y + 0.2 * mm, status_text)

    def draw_field(x, y, w, label, value):
        field_h = 13 * mm
        pdf.setFillColor(colors.HexColor("#F8FAFC"))
        pdf.setStrokeColor(colors.HexColor("#DDE3EC"))
        pdf.roundRect(x, y, w, field_h, 2 * mm, fill=1, stroke=1)
        pdf.setFillColor(colors.HexColor("#64748B"))
        pdf.setFont("Helvetica-Bold", 7.2)
        pdf.drawString(x + 2.5 * mm, y + field_h - 3.8 * mm, label.upper())
        pdf.setFillColor(colors.HexColor("#0F172A"))
        pdf.setFont("Helvetica-Bold", 9.8)
        lines = simpleSplit(str(value or "-"), "Helvetica-Bold", 9.8, w - 5 * mm)
        pdf.drawString(x + 2.5 * mm, y + 4 * mm, lines[0] if lines else "-")

    y = top_y - 24 * mm
    col_gap = 6 * mm
    row_gap = 15 * mm
    col_w = (right_w - col_gap) / 2
    draw_field(right_x, y, col_w, "Claim ID", claim.claim_number)
    draw_field(right_x + col_w + col_gap, y, col_w, "Card Number", claim.warranty_card_number)
    y -= row_gap
    draw_field(right_x, y, col_w, "Order Number", claim.order.order_number)
    draw_field(right_x + col_w + col_gap, y, col_w, "Issued On", generated_at.strftime("%d %b %Y"))
    y -= row_gap
    draw_field(right_x, y, col_w, "Customer", claim.user.get_full_name() or claim.user.username)
    draw_field(right_x + col_w + col_gap, y, col_w, "Email", claim.user.email)
    y -= row_gap
    draw_field(right_x, y, right_w, "Product", claim.product_name)

    # Coverage / claim note (auto generated)
    delivery_dt = (
        claim.order.updated_at
        if claim.order.status == claim.order.Status.DELIVERED
        else claim.order.created_at
    )
    delivery_date = delivery_dt.date()
    claim_start = claim.created_at.date() if claim.created_at else generated_at.date()
    claim_deadline = delivery_date + timedelta(days=7)
    coverage_end = _safe_add_years(claim_start, 2)

    coverage_note_lines = [
        f"Claim Date: {claim_start:%d %b %Y}",
        f"Coverage Period: {claim_start:%d %b %Y} to {coverage_end:%d %b %Y} (24 months)",
        f"Claim Submission Window: within 7 days of delivery (till {claim_deadline:%d %b %Y})",
    ]

    issue_h = 24 * mm
    issue_y = y - 28 * mm
    pdf.setFillColor(colors.HexColor("#FFFFFF"))
    pdf.setStrokeColor(colors.HexColor("#DDE3EC"))
    pdf.roundRect(right_x, issue_y, right_w, issue_h, 2 * mm, fill=1, stroke=1)
    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawString(right_x + 2.5 * mm, issue_y + issue_h - 4.5 * mm, "WARRANTY COVERAGE / CLAIM NOTE")
    pdf.setFillColor(colors.HexColor("#0F172A"))
    text_y = issue_y + issue_h - 8.5 * mm
    for line in coverage_note_lines[:3]:
        text_y = _draw_wrapped_lines(
            pdf=pdf,
            text=line,
            x=right_x + 2.5 * mm,
            y=text_y,
            width=right_w - 5 * mm,
            font_name="Helvetica",
            font_size=8.6,
            line_step=3.8 * mm,
            max_lines=1,
        )
        text_y -= 0.8 * mm

    # Terms and conditions block
    terms_h = 36 * mm
    terms_y = issue_y - terms_h - 7 * mm
    pdf.setFillColor(colors.HexColor("#F8FAFC"))
    pdf.setStrokeColor(colors.HexColor("#DDE3EC"))
    pdf.roundRect(right_x, terms_y, right_w, terms_h, 2 * mm, fill=1, stroke=1)
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(right_x + 2.5 * mm, terms_y + terms_h - 5.5 * mm, "TERMS & CONDITIONS")
    pdf.setFillColor(colors.HexColor("#334155"))
    terms_lines = [
        "1. Warranty is valid for the original purchaser with invoice and this card.",
        "2. Claim must be submitted within 7 days from delivery date.",
        "3. Physical damage, misuse, water ingress, and unauthorized repair are excluded.",
        "4. Coverage validity is 24 months from approved claim date.",
        "5. Support: support@oaltev.com | +91 7291880088.",
    ]
    line_y = terms_y + terms_h - 8.4 * mm
    for term in terms_lines:
        line_y = _draw_wrapped_lines(
            pdf=pdf,
            text=term,
            x=right_x + 2.5 * mm,
            y=line_y,
            width=right_w - 5 * mm,
            font_name="Helvetica",
            font_size=8.0,
            line_step=3.2 * mm,
            max_lines=2,
        )
        line_y -= 0.6 * mm

    # Signature block
    sign_block_y = card_y + 9 * mm
    sign_w = 58 * mm
    sign_h = 18 * mm
    pdf.setFillColor(colors.HexColor("#F8FAFC"))
    pdf.roundRect(right_x, sign_block_y, sign_w, sign_h, 2 * mm, fill=1, stroke=1)
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(right_x + 2.5 * mm, sign_block_y + sign_h - 5.2 * mm, "DIGITAL SIGNATURE")
    _draw_signature(pdf, right_x + 2.5 * mm, sign_block_y + 4.2 * mm, sign_w - 5 * mm, 8 * mm)
    pdf.setStrokeColor(colors.HexColor("#94A3B8"))
    pdf.line(right_x + 2.5 * mm, sign_block_y + 3.5 * mm, right_x + sign_w - 2.5 * mm, sign_block_y + 3.5 * mm)

    # Verify URL / hash text (wrapped)
    verify_x = right_x + sign_w + 4 * mm
    verify_w = right_w - sign_w - 4 * mm
    pdf.setFillColor(colors.HexColor("#475569"))
    pdf.setFont("Helvetica", 7.2)
    verify_base_url = f"{settings.SITE_BASE_URL.rstrip('/')}{reverse('core:verify_document')}"
    pdf.drawString(verify_x, sign_block_y + sign_h - 4.8 * mm, "Verify Endpoint:")
    endpoint_y = _draw_wrapped_lines(
        pdf=pdf,
        text=verify_base_url,
        x=verify_x,
        y=sign_block_y + sign_h - 8.8 * mm,
        width=verify_w,
        font_name="Helvetica",
        font_size=7.0,
        line_step=3.2 * mm,
        max_lines=2,
    )
    pdf.setFont("Helvetica", 7.0)
    pdf.drawString(verify_x, endpoint_y, f"Ref: {claim.claim_number} | Card: {claim.warranty_card_number}")
    pdf.setFont("Helvetica-Bold", 7.2)
    hash_preview = signature_hash if len(signature_hash) <= 36 else f"{signature_hash[:18]}...{signature_hash[-10:]}"
    pdf.drawString(verify_x, max(sign_block_y + 0.5 * mm, endpoint_y - 3.2 * mm), f"Doc Hash: {hash_preview}")

    # Footer legal line
    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.setFont("Helvetica", 8)
    pdf.drawString(
        card_x + 8 * mm,
        card_y + 4.5 * mm,
        "This warranty card is system generated by Oalt EV Technology Pvt. Ltd. Valid as per official warranty policy.",
    )

    pdf.showPage()
    pdf.save()
    data = buffer.getvalue()
    buffer.close()
    return data
