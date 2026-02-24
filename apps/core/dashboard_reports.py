from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _fmt_money(value: Decimal | int | float) -> str:
    amount = Decimal(value or 0).quantize(Decimal("0.01"))
    return f"INR {amount:,.2f}"


def build_dashboard_mis_pdf(
    *,
    period_label: str,
    generated_at,
    order_metrics: dict,
    sales_metrics: dict,
    claims_metrics: dict,
    top_products: list[dict],
    trend_data: list[dict],
) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    page_w, page_h = A4

    # Header
    pdf.setFillColor(colors.HexColor("#C02222"))
    pdf.rect(0, page_h - 35 * mm, page_w, 35 * mm, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(15 * mm, page_h - 16 * mm, "OALT EV MONTHLY MIS REPORT")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(15 * mm, page_h - 23 * mm, f"Period: {period_label}")
    pdf.drawRightString(page_w - 15 * mm, page_h - 23 * mm, f"Generated: {generated_at:%d %b %Y %I:%M %p}")

    # KPI cards
    y = page_h - 45 * mm
    card_w = (page_w - 40 * mm) / 3
    card_h = 22 * mm
    card_titles = ["Orders", "Sales", "Warranty Claims"]
    card_values = [
        str(order_metrics.get("total_orders", 0)),
        _fmt_money(sales_metrics.get("total_revenue", 0)),
        str(claims_metrics.get("total_claims", 0)),
    ]
    card_subtitles = [
        f"Delivered: {order_metrics.get('delivered_orders', 0)} | Cancelled: {order_metrics.get('cancelled_orders', 0)}",
        f"Units sold: {sales_metrics.get('total_qty', 0)}",
        f"Approved: {claims_metrics.get('approved_claims', 0)} | Rejected: {claims_metrics.get('rejected_claims', 0)}",
    ]
    for idx in range(3):
        x = 15 * mm + (idx * (card_w + 5 * mm))
        pdf.setFillColor(colors.HexColor("#F8FAFC"))
        pdf.setStrokeColor(colors.HexColor("#E2E8F0"))
        pdf.roundRect(x, y - card_h, card_w, card_h, 2.5 * mm, stroke=1, fill=1)
        pdf.setFillColor(colors.HexColor("#0F172A"))
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x + 3 * mm, y - 6 * mm, card_titles[idx])
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(x + 3 * mm, y - 12 * mm, card_values[idx])
        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(colors.HexColor("#475569"))
        pdf.drawString(x + 3 * mm, y - 17 * mm, card_subtitles[idx][:56])

    y -= 30 * mm

    # Payment split + claim pipeline
    pdf.setFillColor(colors.HexColor("#FFFFFF"))
    pdf.setStrokeColor(colors.HexColor("#E2E8F0"))
    pdf.roundRect(15 * mm, y - 22 * mm, 88 * mm, 22 * mm, 2 * mm, stroke=1, fill=1)
    pdf.roundRect(107 * mm, y - 22 * mm, 88 * mm, 22 * mm, 2 * mm, stroke=1, fill=1)

    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(18 * mm, y - 6 * mm, "Payment Mix")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(18 * mm, y - 12 * mm, f"Online Orders: {order_metrics.get('online_orders', 0)}")
    pdf.drawString(18 * mm, y - 17 * mm, f"COD Orders: {order_metrics.get('cod_orders', 0)}")

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(110 * mm, y - 6 * mm, "Claim Pipeline")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(
        110 * mm,
        y - 12 * mm,
        f"Submitted: {claims_metrics.get('submitted_claims', 0)} | In Review: {claims_metrics.get('in_review_claims', 0)}",
    )
    pdf.drawString(
        110 * mm,
        y - 17 * mm,
        f"Approved: {claims_metrics.get('approved_claims', 0)} | Resolved: {claims_metrics.get('resolved_claims', 0)}",
    )

    y -= 30 * mm

    # Top products table
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(15 * mm, y, "Top Selling Products")
    y -= 4 * mm
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.rect(15 * mm, y - 7 * mm, 180 * mm, 7 * mm, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawString(18 * mm, y - 5 * mm, "Product")
    pdf.drawString(94 * mm, y - 5 * mm, "Category")
    pdf.drawRightString(154 * mm, y - 5 * mm, "Qty")
    pdf.drawRightString(192 * mm, y - 5 * mm, "Revenue")
    y -= 7 * mm

    pdf.setFont("Helvetica", 8.4)
    for row in (top_products or [])[:8]:
        if y < 75 * mm:
            break
        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(colors.HexColor("#E2E8F0"))
        pdf.rect(15 * mm, y - 6 * mm, 180 * mm, 6 * mm, stroke=1, fill=1)
        pdf.setFillColor(colors.HexColor("#0F172A"))
        pdf.drawString(18 * mm, y - 4.2 * mm, str(row.get("product__name", "-"))[:36])
        pdf.drawString(94 * mm, y - 4.2 * mm, str(row.get("product__category__name", "-"))[:20])
        pdf.drawRightString(154 * mm, y - 4.2 * mm, str(row.get("quantity_sold", 0)))
        pdf.drawRightString(192 * mm, y - 4.2 * mm, _fmt_money(row.get("revenue", 0)))
        y -= 6 * mm

    y -= 6 * mm

    # 6 month trend snapshot
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(15 * mm, y, "6-Month Trend Snapshot")
    y -= 4 * mm
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.rect(15 * mm, y - 7 * mm, 180 * mm, 7 * mm, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawString(18 * mm, y - 5 * mm, "Month")
    pdf.drawRightString(114 * mm, y - 5 * mm, "Orders")
    pdf.drawRightString(150 * mm, y - 5 * mm, "Claims")
    pdf.drawRightString(192 * mm, y - 5 * mm, "Sales")
    y -= 7 * mm

    pdf.setFont("Helvetica", 8.3)
    for row in (trend_data or [])[-6:]:
        if y < 20 * mm:
            break
        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(colors.HexColor("#E2E8F0"))
        pdf.rect(15 * mm, y - 6 * mm, 180 * mm, 6 * mm, stroke=1, fill=1)
        pdf.setFillColor(colors.HexColor("#0F172A"))
        pdf.drawString(18 * mm, y - 4.2 * mm, str(row.get("label", "-")))
        pdf.drawRightString(114 * mm, y - 4.2 * mm, str(row.get("orders", 0)))
        pdf.drawRightString(150 * mm, y - 4.2 * mm, str(row.get("claims", 0)))
        pdf.drawRightString(192 * mm, y - 4.2 * mm, _fmt_money(row.get("sales", 0)))
        y -= 6 * mm

    # Footer
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.drawString(15 * mm, 10 * mm, "Confidential MIS - Oalt EV Technology Pvt. Ltd.")

    pdf.showPage()
    pdf.save()
    data = buffer.getvalue()
    buffer.close()
    return data
