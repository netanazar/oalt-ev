import csv
import hmac
import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import mail_admins
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Prefetch, Q, Sum
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.generic import TemplateView

from apps.accounts.models import WarrantyClaim
from apps.blog.models import BlogPost
from apps.cart.models import Coupon
from apps.core.document_verification import invoice_signature, warranty_signature
from apps.dealership.models import DealershipApplication
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.products.models import Category, Product, ProductVariant

from .dashboard_reports import build_dashboard_mis_pdf
from .forms import ContactInquiryForm, DashboardProductCreateForm, NewsletterForm
from .models import HomeFeatureCard, HomeHeroSlide, HomeModeCard, HomeSectionConfig, SiteContent, Testimonial

LEGAL_PAGES = {
    "privacy-policy": {
        "title": "Privacy Policy",
        "intro": "Your privacy matters to Oalt EV. This policy explains how we collect, use, and protect your data.",
        "sections": [
            {"heading": "Information We Collect", "points": ["Name, email, phone and delivery address for order processing.", "Payment metadata from trusted payment gateway integrations.", "Device and usage analytics to improve user experience and site performance."]},
            {"heading": "How We Use Information", "points": ["To fulfill orders, support returns, and provide customer service.", "To send transaction updates, policy updates, and service reminders.", "To improve products, offers, and website features based on customer behavior."]},
            {"heading": "Data Security", "points": ["Encrypted payment flow via approved gateway providers.", "Restricted admin access and role-based controls.", "Periodic security review and best-practice compliance."]},
        ],
    },
    "terms-conditions": {
        "title": "Terms & Conditions",
        "intro": "By using this website, you agree to the terms listed below for purchases, accounts, and platform usage.",
        "sections": [
            {"heading": "Order and Payment Terms", "points": ["Orders are confirmed after successful payment authorization.", "Prices and availability may change without prior notice.", "Fraudulent or suspicious orders may be canceled after review."]},
            {"heading": "Account Responsibilities", "points": ["Users must provide accurate and current profile details.", "Account misuse or unauthorized activity may result in suspension.", "Passwords and account security are user responsibilities."]},
            {"heading": "Platform Rights", "points": ["Oalt EV can modify, suspend, or discontinue services when required.", "Policy updates become effective after website publication.", "Disputes are subject to applicable jurisdiction and law."]},
        ],
    },
    "return-refund": {
        "title": "Return & Refund Policy",
        "intro": "We strive for a smooth ownership experience. Returns and refunds follow transparent verification rules.",
        "sections": [
            {"heading": "Return Eligibility", "points": ["Return request must be raised within policy window from delivery date.", "Product should be in original condition with accessories and invoice.", "Used, damaged, or altered products may not qualify for return."]},
            {"heading": "Refund Processing", "points": ["Refunds start after inspection and approval.", "Amount is credited to original payment source within banking timelines.", "Gateway and bank processing times may vary by payment method."]},
            {"heading": "Non-Returnable Cases", "points": ["Damage from misuse, unauthorized repairs, or incorrect installation.", "Missing serial tags, mandatory packaging, or essential components.", "Custom-made or special-order inventory unless defective."]},
        ],
    },
    "shipping-terms": {
        "title": "Shipping Terms",
        "intro": "Shipping timelines and serviceability depend on location, product category, and partner logistics.",
        "sections": [
            {"heading": "Dispatch", "points": ["Orders are generally dispatched within 24-48 business hours.", "High-demand or pre-book products may require additional lead time.", "Quality and packaging checks are completed before dispatch."]},
            {"heading": "Delivery", "points": ["Typical delivery window is 3-7 business days for major cities.", "Remote zones may require additional transit time.", "Delivery updates are shared through registered contact channels."]},
            {"heading": "Shipment Exceptions", "points": ["Natural disruptions, holidays, and logistics constraints can delay shipments.", "Address mismatch may result in failed delivery attempts.", "Customers should ensure reachable phone and complete address details."]},
        ],
    },
    "disclaimer": {
        "title": "Disclaimer",
        "intro": "Product visuals, range values, and feature descriptions are indicative and may vary by conditions and usage.",
        "sections": [
            {"heading": "Performance Notice", "points": ["Range and efficiency depend on terrain, load, riding mode, and maintenance.", "Battery performance changes with weather and charging practices.", "Displayed EMI and offer terms are estimates subject to approval."]},
            {"heading": "Content Accuracy", "points": ["We try to keep all content updated and accurate.", "Minor typographical or display errors may occur and can be corrected.", "Latest product specs in official documentation will be final."]},
        ],
    },
    "cancellation-policy": {
        "title": "Cancellation Policy",
        "intro": "Orders can be cancelled under defined timelines and fulfillment stages.",
        "sections": [
            {"heading": "Before Dispatch", "points": ["Orders can be canceled quickly before shipment processing.", "Instant payment reversal will be initiated on approval."]},
            {"heading": "After Dispatch", "points": ["Post-dispatch cancellation may not be available.", "Customer may use return policy after successful delivery if eligible."]},
        ],
    },
    "warranty-policy": {
        "title": "Warranty Policy",
        "intro": "Oalt EV products are backed by warranty coverage against manufacturing defects.",
        "sections": [
            {"heading": "Coverage", "points": ["Warranty includes covered components as per invoice and product plan.", "Battery and motor coverage follows defined model-specific periods."]},
            {"heading": "Exclusions", "points": ["Accidental damage, negligence, and unauthorized repairs are excluded.", "Consumables and cosmetic wear are not covered unless stated."]},
            {"heading": "Claim Process", "points": ["Share invoice and issue details with support team.", "Service center inspection determines claim acceptance."]},
        ],
    },
    "faq": {
        "title": "Frequently Asked Questions",
        "intro": "Quick answers to common buyer and ownership questions.",
        "sections": [
            {"heading": "Buying", "points": ["Can I purchase on EMI? Yes, subject to partner approval.", "Can I book test ride? Yes, use WhatsApp or contact page to request."]},
            {"heading": "Ownership", "points": ["How often service is needed? Preventive check every 3 months recommended.", "Can I ride without assist? Yes, manual and assist modes are available."]},
        ],
    },
    "cookies-policy": {
        "title": "Cookies Policy",
        "intro": "We use cookies to improve site functionality, analytics, and personalization.",
        "sections": [
            {"heading": "Cookie Usage", "points": ["Session management and secure checkout continuity.", "Performance analytics and error tracking for better reliability.", "Remembering preferences for improved user experience."]},
            {"heading": "Your Control", "points": ["You can block cookies from browser settings.", "Certain features may not work correctly if cookies are disabled."]},
        ],
    },
}


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        featured_products = Product.objects.filter(is_featured=True, is_active=True).prefetch_related(
            Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True).only("id", "product_id", "color_code"))
        )[:8]
        hero_slides = HomeHeroSlide.objects.filter(is_active=True).only("title", "subtitle", "cta_text", "cta_url", "image", "order")[:6]
        context["featured_products"] = featured_products
        context["latest_posts"] = BlogPost.objects.filter(is_published=True)[:4]
        context["testimonials"] = Testimonial.objects.filter(is_active=True)[:12]
        context["hero_slides"] = hero_slides
        context["feature_cards"] = HomeFeatureCard.objects.filter(is_active=True).only("title", "description", "image", "card_type", "order")[:6]
        context["mode_cards"] = HomeModeCard.objects.filter(is_active=True).only("title", "description", "image", "order")[:6]
        configs = HomeSectionConfig.objects.filter(is_active=True).only("key", "heading", "subheading", "cta_text", "cta_url", "image")
        context["home_sections"] = {item.key: item for item in configs}
        site_content_items = SiteContent.objects.filter(
            is_active=True,
            key__in=[
                "hero_visual_mode",
                "hero_background_image",
                "hero_product_image",
                "hero_heading",
                "hero_subheading",
                "hero_cta",
            ],
        ).only("key", "title", "subtitle", "image")
        site_content_map = {item.key: item for item in site_content_items}

        hero_mode_item = site_content_map.get("hero_visual_mode")
        hero_visual_mode = (hero_mode_item.title.strip().lower() if hero_mode_item and hero_mode_item.title else "gradient")
        if hero_visual_mode not in {"gradient", "image"}:
            hero_visual_mode = "gradient"

        hero_bg_item = site_content_map.get("hero_background_image")
        hero_bg_url = ""
        if hero_bg_item and hero_bg_item.image:
            hero_bg_url = hero_bg_item.image.url
        elif hero_slides:
            hero_bg_url = hero_slides[0].image.url
        else:
            hero_bg_url = "/media/hero-luxury-bg.jpg"

        hero_bike_item = site_content_map.get("hero_product_image")
        hero_bike_url = ""
        if hero_bike_item and hero_bike_item.image:
            hero_bike_url = hero_bike_item.image.url
        elif featured_products:
            hero_bike_url = featured_products[0].main_image.url
        else:
            hero_bike_url = "/media/hero-bike.png"

        hero_heading_item = site_content_map.get("hero_heading")
        hero_subheading_item = site_content_map.get("hero_subheading")
        hero_cta_item = site_content_map.get("hero_cta")

        context["hero_visual_mode"] = hero_visual_mode
        context["hero_bg_url"] = hero_bg_url
        context["hero_bike_url"] = hero_bike_url
        context["hero_heading"] = hero_heading_item.title if hero_heading_item and hero_heading_item.title else "Experience the Future of Riding"
        context["hero_subheading"] = hero_subheading_item.title if hero_subheading_item and hero_subheading_item.title else "OALT Premium Electric Bike"
        context["hero_cta_text"] = hero_cta_item.title if hero_cta_item and hero_cta_item.title else "Explore Now"
        context["hero_cta_url"] = hero_cta_item.subtitle if hero_cta_item and hero_cta_item.subtitle else "/shop/"
        context["newsletter_form"] = NewsletterForm()
        return context


def newsletter_subscribe(request):
    if request.method == "POST":
        form = NewsletterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Subscribed successfully.")
        else:
            messages.error(request, "This email is already subscribed.")
    return redirect("core:home")


def _shift_month(base_month: date, delta: int) -> date:
    month_index = base_month.year * 12 + (base_month.month - 1) + delta
    return date(month_index // 12, (month_index % 12) + 1, 1)


def _report_period(year: int, month: int):
    month_start = date(year, month, 1)
    next_month = _shift_month(month_start, 1)
    month_end = next_month - timedelta(days=1)
    month_start_dt = timezone.make_aware(datetime.combine(month_start, datetime.min.time()))
    month_end_dt = timezone.make_aware(datetime.combine(month_end, datetime.max.time()))
    return month_start, month_end, month_start_dt, month_end_dt


def _safe_int(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _parse_iso_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _dashboard_period_from_request(request, today: date):
    selected_year = _safe_int(request.GET.get("year"), today.year)
    selected_month = _safe_int(request.GET.get("month"), today.month)
    if selected_month < 1 or selected_month > 12:
        selected_month = today.month

    from_date_raw = (request.GET.get("from_date") or "").strip()
    to_date_raw = (request.GET.get("to_date") or "").strip()
    from_date = _parse_iso_date(from_date_raw)
    to_date = _parse_iso_date(to_date_raw)

    if from_date and to_date:
        if from_date > to_date:
            from_date, to_date = to_date, from_date
        range_start = from_date
        range_end = to_date
        filter_mode = "custom"
        current_range = f"{range_start:%d %b %Y} - {range_end:%d %b %Y}"
        query_string = f"from_date={range_start.isoformat()}&to_date={range_end.isoformat()}"
    else:
        range_start, range_end, _, _ = _report_period(selected_year, selected_month)
        filter_mode = "monthly"
        current_range = f"{range_start:%d %b %Y} - {range_end:%d %b %Y}"
        query_string = f"month={selected_month}&year={selected_year}"
        from_date_raw = ""
        to_date_raw = ""

    range_start_dt = timezone.make_aware(datetime.combine(range_start, datetime.min.time()))
    range_end_dt = timezone.make_aware(datetime.combine(range_end, datetime.max.time()))
    return {
        "selected_year": selected_year,
        "selected_month": selected_month,
        "from_date": from_date_raw,
        "to_date": to_date_raw,
        "filter_mode": filter_mode,
        "range_start": range_start,
        "range_end": range_end,
        "range_start_dt": range_start_dt,
        "range_end_dt": range_end_dt,
        "current_range": current_range,
        "query_string": query_string,
    }


def _dashboard_section_links():
    return {
        "categories": reverse("core:dashboard_manage", kwargs={"section": "categories"}),
        "products": reverse("core:dashboard_manage", kwargs={"section": "products"}),
        "orders": reverse("core:dashboard_manage", kwargs={"section": "orders"}),
        "warranty": reverse("core:dashboard_manage", kwargs={"section": "warranty"}),
        "payments": reverse("core:dashboard_manage", kwargs={"section": "payments"}),
        "coupons": reverse("core:dashboard_manage", kwargs={"section": "coupons"}),
        "dealership": reverse("core:dashboard_manage", kwargs={"section": "dealership"}),
        "blog": reverse("core:dashboard_manage", kwargs={"section": "blog"}),
        "home_content": reverse("core:dashboard_manage", kwargs={"section": "home-content"}),
        "admin_site": reverse("admin:index"),
    }


def _sales_aggregate(items_qs):
    return items_qs.aggregate(
        total_qty=Sum("quantity"),
        total_revenue=Sum(
            ExpressionWrapper(F("quantity") * F("price"), output_field=DecimalField(max_digits=14, decimal_places=2))
        ),
    )


@staff_member_required(login_url="accounts:login")
def dashboard(request):
    today = timezone.localdate()
    period = _dashboard_period_from_request(request, today)

    if request.method == "POST" and request.POST.get("action") == "create_category":
        category_name = (request.POST.get("category_name") or "").strip()
        category_description = (request.POST.get("category_description") or "").strip()
        category_parent = (request.POST.get("category_parent") or "").strip()
        category_active = request.POST.get("category_is_active") == "on"

        if not category_name:
            messages.error(request, "Category name is required.")
            return redirect("core:dashboard")

        slug_base = slugify(category_name) or f"category-{timezone.now().strftime('%H%M%S')}"
        slug = slug_base
        counter = 2
        while Category.objects.filter(slug=slug).exists():
            slug = f"{slug_base}-{counter}"
            counter += 1

        category = Category(
            name=category_name,
            slug=slug,
            description=category_description,
            is_active=category_active,
        )
        if category_parent:
            category.parent_id = _safe_int(category_parent, None)
        try:
            category.full_clean()
            category.save()
            messages.success(request, f"Category '{category.name}' created successfully.")
        except ValidationError as exc:
            messages.error(request, f"Category not created: {exc}")
        return redirect(f"{reverse('core:dashboard')}?{period['query_string']}")

    monthly_orders = (
        Order.objects.filter(created_at__range=(period["range_start_dt"], period["range_end_dt"]))
        .select_related("user")
        .prefetch_related("items", "items__product")
    )
    monthly_order_items = OrderItem.objects.filter(
        order__created_at__range=(period["range_start_dt"], period["range_end_dt"])
    ).select_related("product")
    monthly_claims = WarrantyClaim.objects.filter(
        created_at__range=(period["range_start_dt"], period["range_end_dt"])
    ).select_related("user", "order")

    order_metrics = monthly_orders.aggregate(
        total_orders=Count("id"),
        delivered_orders=Count("id", filter=Q(status=Order.Status.DELIVERED)),
        paid_orders=Count("id", filter=Q(status=Order.Status.PAID)),
        shipped_orders=Count("id", filter=Q(status=Order.Status.SHIPPED)),
        cancelled_orders=Count("id", filter=Q(status=Order.Status.CANCELLED)),
        cod_orders=Count("id", filter=Q(payment_method=Order.PaymentMethod.COD)),
        online_orders=Count("id", filter=Q(payment_method=Order.PaymentMethod.ONLINE)),
        gross_sales=Sum("total_amount"),
    )

    sales_metrics = _sales_aggregate(monthly_order_items)
    claims_metrics = monthly_claims.aggregate(
        total_claims=Count("id"),
        submitted_claims=Count("id", filter=Q(status=WarrantyClaim.Status.SUBMITTED)),
        in_review_claims=Count("id", filter=Q(status=WarrantyClaim.Status.IN_REVIEW)),
        approved_claims=Count("id", filter=Q(status=WarrantyClaim.Status.APPROVED)),
        rejected_claims=Count("id", filter=Q(status=WarrantyClaim.Status.REJECTED)),
        resolved_claims=Count("id", filter=Q(status=WarrantyClaim.Status.RESOLVED)),
    )

    monthly_top_products = (
        monthly_order_items.values("product__name", "product__slug", "product__category__name")
        .annotate(
            quantity_sold=Sum("quantity"),
            revenue=Sum(
                ExpressionWrapper(F("quantity") * F("price"), output_field=DecimalField(max_digits=14, decimal_places=2))
            ),
        )
        .order_by("-quantity_sold", "-revenue")[:10]
    )

    low_stock_products = Product.objects.filter(is_active=True, stock__lte=5).select_related("category").order_by("stock", "name")[:10]

    monthly_trend = []
    base_month = date(period["range_end"].year, period["range_end"].month, 1)
    for offset in range(-5, 1):
        point_month = _shift_month(base_month, offset)
        p_start, _p_end, p_start_dt, p_end_dt = _report_period(point_month.year, point_month.month)
        p_orders = Order.objects.filter(created_at__range=(p_start_dt, p_end_dt))
        p_items = OrderItem.objects.filter(order__created_at__range=(p_start_dt, p_end_dt))
        p_claims = WarrantyClaim.objects.filter(created_at__range=(p_start_dt, p_end_dt))

        point_sales = _sales_aggregate(p_items)
        monthly_trend.append(
            {
                "label": p_start.strftime("%b %Y"),
                "orders": p_orders.count(),
                "sales": point_sales.get("total_revenue") or Decimal("0.00"),
                "claims": p_claims.count(),
            }
        )

    year_choices = list(range(today.year - 3, today.year + 2))
    payment_split_total = (order_metrics.get("online_orders") or 0) + (order_metrics.get("cod_orders") or 0)

    chart_data = {
        "trend_labels": [item["label"] for item in monthly_trend],
        "trend_orders": [item["orders"] for item in monthly_trend],
        "trend_sales": [float(item["sales"] or 0) for item in monthly_trend],
        "trend_claims": [item["claims"] for item in monthly_trend],
        "payment_labels": ["Online", "COD"],
        "payment_values": [order_metrics.get("online_orders") or 0, order_metrics.get("cod_orders") or 0],
        "claim_labels": ["Submitted", "In Review", "Approved", "Rejected", "Resolved"],
        "claim_values": [
            claims_metrics.get("submitted_claims") or 0,
            claims_metrics.get("in_review_claims") or 0,
            claims_metrics.get("approved_claims") or 0,
            claims_metrics.get("rejected_claims") or 0,
            claims_metrics.get("resolved_claims") or 0,
        ],
    }

    context = {
        "total_products": Product.objects.count(),
        "total_posts": BlogPost.objects.count(),
        "total_orders": Order.objects.count(),
        "total_payments": Payment.objects.count(),
        "total_categories": Category.objects.count(),
        "total_warranty_claims": WarrantyClaim.objects.count(),
        "total_dealership_applications": DealershipApplication.objects.count(),
        "total_coupons": Coupon.objects.count(),
        "dashboard_links": _dashboard_section_links(),
        "admin_url": reverse("admin:index"),
        "category_options": Category.objects.select_related("parent").order_by("parent__name", "name"),
        "selected_year": period["selected_year"],
        "selected_month": period["selected_month"],
        "from_date": period["from_date"],
        "to_date": period["to_date"],
        "filter_mode": period["filter_mode"],
        "report_query_string": period["query_string"],
        "year_choices": year_choices,
        "month_choices": range(1, 13),
        "current_month_range": period["current_range"],
        "monthly_orders": monthly_orders[:12],
        "monthly_claims": monthly_claims[:10],
        "monthly_top_products": monthly_top_products,
        "low_stock_products": low_stock_products,
        "monthly_trend": monthly_trend,
        "chart_data_json": json.dumps(chart_data),
        "payment_split_total": payment_split_total,
        "order_metrics": {
            "total_orders": order_metrics.get("total_orders") or 0,
            "delivered_orders": order_metrics.get("delivered_orders") or 0,
            "paid_orders": order_metrics.get("paid_orders") or 0,
            "shipped_orders": order_metrics.get("shipped_orders") or 0,
            "cancelled_orders": order_metrics.get("cancelled_orders") or 0,
            "cod_orders": order_metrics.get("cod_orders") or 0,
            "online_orders": order_metrics.get("online_orders") or 0,
            "gross_sales": order_metrics.get("gross_sales") or Decimal("0.00"),
        },
        "sales_metrics": {
            "total_qty": sales_metrics.get("total_qty") or 0,
            "total_revenue": sales_metrics.get("total_revenue") or Decimal("0.00"),
        },
        "claims_metrics": {
            "total_claims": claims_metrics.get("total_claims") or 0,
            "submitted_claims": claims_metrics.get("submitted_claims") or 0,
            "in_review_claims": claims_metrics.get("in_review_claims") or 0,
            "approved_claims": claims_metrics.get("approved_claims") or 0,
            "rejected_claims": claims_metrics.get("rejected_claims") or 0,
            "resolved_claims": claims_metrics.get("resolved_claims") or 0,
        },
        "recent_orders": Order.objects.select_related("user").prefetch_related("items", "items__product")[:8],
        "recent_dealership_applications": DealershipApplication.objects.all()[:8],
    }
    return render(request, "dashboard/index.html", context)


@staff_member_required(login_url="accounts:login")
def dashboard_export_report(request, report_type):
    today = timezone.localdate()
    period = _dashboard_period_from_request(request, today)
    month_label = period["range_start"].strftime("%b-%Y").lower()
    if period["filter_mode"] == "custom":
        month_label = f"{period['range_start']:%Y%m%d}-{period['range_end']:%Y%m%d}"

    if report_type not in {"orders", "sales", "warranty", "mis"}:
        return HttpResponseBadRequest("Unsupported report type.")

    orders_in_range = Order.objects.filter(created_at__range=(period["range_start_dt"], period["range_end_dt"]))
    order_items_in_range = OrderItem.objects.filter(order__created_at__range=(period["range_start_dt"], period["range_end_dt"]))
    claims_in_range = WarrantyClaim.objects.filter(created_at__range=(period["range_start_dt"], period["range_end_dt"]))

    if report_type == "mis":
        order_metrics = orders_in_range.aggregate(
            total_orders=Count("id"),
            delivered_orders=Count("id", filter=Q(status=Order.Status.DELIVERED)),
            cancelled_orders=Count("id", filter=Q(status=Order.Status.CANCELLED)),
            cod_orders=Count("id", filter=Q(payment_method=Order.PaymentMethod.COD)),
            online_orders=Count("id", filter=Q(payment_method=Order.PaymentMethod.ONLINE)),
            gross_sales=Sum("total_amount"),
        )
        sales_metrics = _sales_aggregate(order_items_in_range)
        claims_metrics = claims_in_range.aggregate(
            total_claims=Count("id"),
            submitted_claims=Count("id", filter=Q(status=WarrantyClaim.Status.SUBMITTED)),
            in_review_claims=Count("id", filter=Q(status=WarrantyClaim.Status.IN_REVIEW)),
            approved_claims=Count("id", filter=Q(status=WarrantyClaim.Status.APPROVED)),
            rejected_claims=Count("id", filter=Q(status=WarrantyClaim.Status.REJECTED)),
            resolved_claims=Count("id", filter=Q(status=WarrantyClaim.Status.RESOLVED)),
        )

        top_products = list(
            order_items_in_range.values("product__name", "product__category__name")
            .annotate(
                quantity_sold=Sum("quantity"),
                revenue=Sum(
                    ExpressionWrapper(F("quantity") * F("price"), output_field=DecimalField(max_digits=14, decimal_places=2))
                ),
            )
            .order_by("-quantity_sold", "-revenue")[:8]
        )
        trend_data = []
        base_month = date(period["range_end"].year, period["range_end"].month, 1)
        for offset in range(-5, 1):
            point_month = _shift_month(base_month, offset)
            p_start, _p_end, p_start_dt, p_end_dt = _report_period(point_month.year, point_month.month)
            p_orders = Order.objects.filter(created_at__range=(p_start_dt, p_end_dt))
            p_items = OrderItem.objects.filter(order__created_at__range=(p_start_dt, p_end_dt))
            p_claims = WarrantyClaim.objects.filter(created_at__range=(p_start_dt, p_end_dt))
            point_sales = _sales_aggregate(p_items)
            trend_data.append(
                {
                    "label": p_start.strftime("%b %Y"),
                    "orders": p_orders.count(),
                    "sales": point_sales.get("total_revenue") or Decimal("0.00"),
                    "claims": p_claims.count(),
                }
            )

        pdf_data = build_dashboard_mis_pdf(
            period_label=period["current_range"],
            generated_at=timezone.now(),
            order_metrics={
                "total_orders": order_metrics.get("total_orders") or 0,
                "delivered_orders": order_metrics.get("delivered_orders") or 0,
                "cancelled_orders": order_metrics.get("cancelled_orders") or 0,
                "cod_orders": order_metrics.get("cod_orders") or 0,
                "online_orders": order_metrics.get("online_orders") or 0,
                "gross_sales": order_metrics.get("gross_sales") or Decimal("0.00"),
            },
            sales_metrics={
                "total_qty": sales_metrics.get("total_qty") or 0,
                "total_revenue": sales_metrics.get("total_revenue") or Decimal("0.00"),
            },
            claims_metrics={
                "total_claims": claims_metrics.get("total_claims") or 0,
                "submitted_claims": claims_metrics.get("submitted_claims") or 0,
                "in_review_claims": claims_metrics.get("in_review_claims") or 0,
                "approved_claims": claims_metrics.get("approved_claims") or 0,
                "rejected_claims": claims_metrics.get("rejected_claims") or 0,
                "resolved_claims": claims_metrics.get("resolved_claims") or 0,
            },
            top_products=top_products,
            trend_data=trend_data,
        )
        response = HttpResponse(pdf_data, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="oalt-mis-report-{month_label}.pdf"'
        return response

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="oalt-{report_type}-report-{month_label}.csv"'
    writer = csv.writer(response)

    if report_type == "orders":
        writer.writerow(
            [
                "Order Number",
                "Date",
                "Customer",
                "Status",
                "Payment Method",
                "Subtotal (INR)",
                "Discount (INR)",
                "GST (INR)",
                "Total (INR)",
            ]
        )
        orders = (
            orders_in_range
            .select_related("user")
            .order_by("-created_at")
        )
        for order in orders:
            writer.writerow(
                [
                    order.order_number,
                    timezone.localtime(order.created_at).strftime("%Y-%m-%d %H:%M"),
                    order.user.get_full_name() or order.user.username,
                    order.get_status_display(),
                    order.get_payment_method_display(),
                    order.subtotal,
                    order.discount,
                    order.gst,
                    order.total_amount,
                ]
            )
        return response

    if report_type == "sales":
        writer.writerow(["Product", "Category", "Quantity Sold", "Revenue (INR)"])
        rows = (
            order_items_in_range
            .values("product__name", "product__category__name")
            .annotate(
                quantity_sold=Sum("quantity"),
                revenue=Sum(
                    ExpressionWrapper(F("quantity") * F("price"), output_field=DecimalField(max_digits=14, decimal_places=2))
                ),
            )
            .order_by("-quantity_sold", "-revenue")
        )
        for row in rows:
            writer.writerow(
                [
                    row.get("product__name"),
                    row.get("product__category__name"),
                    row.get("quantity_sold") or 0,
                    row.get("revenue") or Decimal("0.00"),
                ]
            )
        return response

    writer.writerow(["Claim Number", "Date", "Order Number", "Card Number", "Customer", "Status", "Product"])
    claims = (
        claims_in_range
        .select_related("order", "user")
        .order_by("-created_at")
    )
    for claim in claims:
        writer.writerow(
            [
                claim.claim_number,
                timezone.localtime(claim.created_at).strftime("%Y-%m-%d %H:%M"),
                claim.order.order_number,
                claim.warranty_card_number,
                claim.user.get_full_name() or claim.user.username,
                claim.get_status_display(),
                claim.product_name,
            ]
        )
    return response


DASHBOARD_MANAGE_SECTIONS = {
    "categories": {"title": "Category Management", "icon": "fa-layer-group"},
    "products": {"title": "Product Management", "icon": "fa-bicycle"},
    "orders": {"title": "Order Management", "icon": "fa-box-open"},
    "warranty": {"title": "Warranty Claim Management", "icon": "fa-id-card"},
    "payments": {"title": "Payment Logs", "icon": "fa-money-check-dollar"},
    "coupons": {"title": "Coupon Management", "icon": "fa-ticket"},
    "dealership": {"title": "Dealership Applications", "icon": "fa-handshake"},
    "blog": {"title": "Blog Management", "icon": "fa-newspaper"},
    "home-content": {"title": "Homepage Content", "icon": "fa-house-signal"},
}


@staff_member_required(login_url="accounts:login")
def dashboard_manage(request, section):
    if section not in DASHBOARD_MANAGE_SECTIONS:
        messages.error(request, "Invalid management section.")
        return redirect("core:dashboard")

    today = timezone.localdate()
    period = _dashboard_period_from_request(request, today)
    search_query = (request.GET.get("q") or "").strip()
    product_create_form = DashboardProductCreateForm() if section == "products" else None

    def _redirect_self():
        query = period["query_string"]
        if search_query:
            query = f"{query}&q={search_query}"
        return redirect(f"{reverse('core:dashboard_manage', kwargs={'section': section})}?{query}")

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        if section == "orders" and action == "update_order":
            order = Order.objects.filter(id=request.POST.get("order_id")).first()
            if order:
                status = request.POST.get("status")
                payment_method = request.POST.get("payment_method")
                if status in Order.Status.values:
                    order.status = status
                if payment_method in Order.PaymentMethod.values:
                    order.payment_method = payment_method
                order.save(update_fields=["status", "payment_method", "updated_at"])
                messages.success(request, f"Order {order.order_number} updated.")
            return _redirect_self()

        if section == "warranty" and action == "update_claim":
            claim = WarrantyClaim.objects.filter(id=request.POST.get("claim_id")).first()
            if claim:
                status = request.POST.get("status")
                if status in WarrantyClaim.Status.values:
                    claim.status = status
                    claim.save(update_fields=["status", "updated_at"])
                    messages.success(request, f"Claim {claim.claim_number} updated.")
            return _redirect_self()

        if section == "products" and action == "update_product":
            product = Product.objects.filter(id=request.POST.get("product_id")).first()
            if product:
                stock = _safe_int(request.POST.get("stock"), product.stock)
                if stock is None:
                    stock = product.stock
                product.stock = max(stock, 0)
                product.is_active = request.POST.get("is_active") == "on"
                product.is_featured = request.POST.get("is_featured") == "on"
                product.save(update_fields=["stock", "is_active", "is_featured", "updated_at"])
                messages.success(request, f"Product '{product.name}' updated.")
            return _redirect_self()

        if section == "products" and action == "create_product":
            product_create_form = DashboardProductCreateForm(request.POST, request.FILES)
            if product_create_form.is_valid():
                created_product = product_create_form.save()
                messages.success(request, f"New product '{created_product.name}' listed successfully.")
                return _redirect_self()
            messages.error(request, "Please fix the product listing form errors and submit again.")

        if section == "categories" and action == "toggle_category":
            category = Category.objects.filter(id=request.POST.get("category_id")).first()
            if category:
                category.is_active = not category.is_active
                category.save(update_fields=["is_active"])
                messages.success(request, f"Category '{category.name}' status updated.")
            return _redirect_self()

        if section == "coupons" and action == "toggle_coupon":
            coupon = Coupon.objects.filter(id=request.POST.get("coupon_id")).first()
            if coupon:
                coupon.active = not coupon.active
                coupon.save(update_fields=["active"])
                messages.success(request, f"Coupon '{coupon.code}' status updated.")
            return _redirect_self()

        if section == "blog" and action == "toggle_blog":
            post = BlogPost.objects.filter(id=request.POST.get("post_id")).first()
            if post:
                post.is_published = not post.is_published
                post.save(update_fields=["is_published"])
                messages.success(request, f"Blog '{post.title}' status updated.")
            return _redirect_self()

    data_queryset = None
    if section == "categories":
        data_queryset = Category.objects.select_related("parent").order_by("parent__name", "name")
        if search_query:
            data_queryset = data_queryset.filter(Q(name__icontains=search_query) | Q(parent__name__icontains=search_query))
    elif section == "products":
        data_queryset = Product.objects.select_related("category").order_by("-updated_at")
        if search_query:
            data_queryset = data_queryset.filter(Q(name__icontains=search_query) | Q(category__name__icontains=search_query))
    elif section == "orders":
        data_queryset = (
            Order.objects.filter(created_at__range=(period["range_start_dt"], period["range_end_dt"]))
            .select_related("user")
            .order_by("-created_at")
        )
        if search_query:
            data_queryset = data_queryset.filter(
                Q(order_number__icontains=search_query) | Q(user__username__icontains=search_query) | Q(user__email__icontains=search_query)
            )
    elif section == "warranty":
        data_queryset = (
            WarrantyClaim.objects.filter(created_at__range=(period["range_start_dt"], period["range_end_dt"]))
            .select_related("user", "order")
            .order_by("-created_at")
        )
        if search_query:
            data_queryset = data_queryset.filter(
                Q(claim_number__icontains=search_query)
                | Q(warranty_card_number__icontains=search_query)
                | Q(product_name__icontains=search_query)
            )
    elif section == "payments":
        data_queryset = (
            Payment.objects.filter(created_at__range=(period["range_start_dt"], period["range_end_dt"]))
            .select_related("order", "order__user")
            .order_by("-created_at")
        )
        if search_query:
            data_queryset = data_queryset.filter(
                Q(order__order_number__icontains=search_query)
                | Q(provider_payment_id__icontains=search_query)
                | Q(provider_order_id__icontains=search_query)
            )
    elif section == "coupons":
        data_queryset = Coupon.objects.order_by("-valid_to")
        if search_query:
            data_queryset = data_queryset.filter(code__icontains=search_query)
    elif section == "dealership":
        data_queryset = DealershipApplication.objects.filter(
            created_at__range=(period["range_start_dt"], period["range_end_dt"])
        ).order_by("-created_at")
        if search_query:
            data_queryset = data_queryset.filter(Q(name__icontains=search_query) | Q(city__icontains=search_query))
    elif section == "blog":
        data_queryset = BlogPost.objects.order_by("-published_at")
        if search_query:
            data_queryset = data_queryset.filter(title__icontains=search_query)
    elif section == "home-content":
        data_queryset = HomeSectionConfig.objects.order_by("key", "heading")
        if search_query:
            data_queryset = data_queryset.filter(Q(key__icontains=search_query) | Q(heading__icontains=search_query))

    paginator = Paginator(data_queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "section": section,
        "section_meta": DASHBOARD_MANAGE_SECTIONS[section],
        "sections": DASHBOARD_MANAGE_SECTIONS,
        "page_obj": page_obj,
        "search_query": search_query,
        "current_month_range": period["current_range"],
        "from_date": period["from_date"],
        "to_date": period["to_date"],
        "selected_month": period["selected_month"],
        "selected_year": period["selected_year"],
        "month_choices": range(1, 13),
        "year_choices": list(range(today.year - 3, today.year + 2)),
        "status_choices": Order.Status.choices,
        "payment_method_choices": Order.PaymentMethod.choices,
        "claim_status_choices": WarrantyClaim.Status.choices,
        "dashboard_links": _dashboard_section_links(),
        "admin_url": reverse("admin:index"),
        "product_create_form": product_create_form,
    }
    return render(request, "dashboard/manage.html", context)


def about_us(request):
    context = {
        "title": "About Us",
        "intro": "Oalt EV Technology Pvt. Ltd. is building India-first electric mobility products for modern riders and cities.",
        "sections": [
            {"heading": "Our Mission", "points": ["Make EV adoption practical, reliable, and aspirational.", "Deliver premium products with strong after-sales support."]},
            {"heading": "What We Build", "points": ["Electric bikes and EV mobility products for D2C customers.", "Dealership-led last-mile and city mobility ecosystem."]},
            {"heading": "Why Oalt EV", "points": ["Performance-focused product engineering.", "Transparent pricing, support, and service commitment."]},
        ],
    }
    return render(request, "core/pages/content_page.html", context)


def contact_us(request):
    if request.method == "POST":
        form = ContactInquiryForm(request.POST)
        if form.is_valid():
            inquiry = form.save()
            mail_admins("New Contact Inquiry", f"{inquiry.name} | {inquiry.email} | {inquiry.subject}", fail_silently=True)
            messages.success(request, "Thanks, your inquiry has been submitted.")
            return redirect("core:contact_us")
    else:
        form = ContactInquiryForm()
    return render(request, "core/pages/contact_us.html", {"form": form})


def legal_page(request, slug):
    page = LEGAL_PAGES.get(slug)
    if not page:
        return redirect("core:home")
    return render(request, "core/pages/content_page.html", page)


def verify_document(request):
    doc_type = (request.GET.get("type") or "").strip().lower()
    reference = (request.GET.get("ref") or "").strip()
    signature = (request.GET.get("sig") or "").strip().upper()
    ts_raw = (request.GET.get("ts") or "").strip()
    order_ref = (request.GET.get("order") or "").strip()
    card_ref = (request.GET.get("card") or "").strip()

    context = {
        "doc_type": doc_type,
        "reference": reference,
        "verification_status": "pending",
        "status_title": "Ready To Verify",
        "status_text": "Scan QR from invoice/warranty card, or open link with verification params.",
        "document_data": [],
    }

    if not all([doc_type, reference, signature, ts_raw]):
        return render(request, "core/pages/verify_document.html", context)

    try:
        issued_ts = int(ts_raw)
    except ValueError:
        context.update(
            {
                "verification_status": "invalid",
                "status_title": "Invalid Timestamp",
                "status_text": "Timestamp in verification link is not valid.",
            }
        )
        return render(request, "core/pages/verify_document.html", context)

    if doc_type == "invoice":
        order = Order.objects.filter(order_number=reference).select_related("user").first()
        if not order:
            context.update(
                {
                    "verification_status": "invalid",
                    "status_title": "Invoice Not Found",
                    "status_text": "No order matched this invoice reference.",
                }
            )
            return render(request, "core/pages/verify_document.html", context)

        expected = invoice_signature(order.order_number, order.total_amount, issued_ts)
        verified = hmac.compare_digest(expected, signature)
        context.update(
            {
                "verification_status": "verified" if verified else "invalid",
                "status_title": "Invoice Verified" if verified else "Invoice Verification Failed",
                "status_text": "Invoice is authentic and issued by Oalt EV." if verified else "Invoice signature mismatch.",
                "document_data": [
                    ("Document Type", "Invoice"),
                    ("Order Number", order.order_number),
                    ("Customer", order.user.get_full_name() or order.user.username),
                    ("Total Amount", f"INR {order.total_amount}"),
                    ("Order Status", order.get_status_display()),
                    ("Issued Timestamp", str(issued_ts)),
                    ("Document Hash", signature),
                ],
            }
        )
        return render(request, "core/pages/verify_document.html", context)

    if doc_type == "warranty":
        claim = WarrantyClaim.objects.filter(claim_number=reference).select_related("order", "user").first()
        if not claim:
            context.update(
                {
                    "verification_status": "invalid",
                    "status_title": "Warranty Claim Not Found",
                    "status_text": "No warranty claim matched this reference.",
                }
            )
            return render(request, "core/pages/verify_document.html", context)

        if order_ref and claim.order.order_number != order_ref:
            context.update(
                {
                    "verification_status": "invalid",
                    "status_title": "Order Mismatch",
                    "status_text": "Warranty link order reference does not match claim record.",
                }
            )
            return render(request, "core/pages/verify_document.html", context)

        if card_ref and claim.warranty_card_number != card_ref:
            context.update(
                {
                    "verification_status": "invalid",
                    "status_title": "Card Number Mismatch",
                    "status_text": "Warranty card number mismatch in verification link.",
                }
            )
            return render(request, "core/pages/verify_document.html", context)

        expected = warranty_signature(claim.claim_number, claim.warranty_card_number, claim.order.order_number, issued_ts)
        verified = hmac.compare_digest(expected, signature)
        context.update(
            {
                "verification_status": "verified" if verified else "invalid",
                "status_title": "Warranty Card Verified" if verified else "Warranty Verification Failed",
                "status_text": "Warranty card is authentic and issued by Oalt EV." if verified else "Warranty signature mismatch.",
                "document_data": [
                    ("Document Type", "Warranty Card"),
                    ("Claim Number", claim.claim_number),
                    ("Warranty Card", claim.warranty_card_number),
                    ("Order Number", claim.order.order_number),
                    ("Customer", claim.user.get_full_name() or claim.user.username),
                    ("Claim Status", claim.get_status_display()),
                    ("Issued Timestamp", str(issued_ts)),
                    ("Document Hash", signature),
                ],
            }
        )
        return render(request, "core/pages/verify_document.html", context)

    context.update(
        {
            "verification_status": "invalid",
            "status_title": "Unsupported Document Type",
            "status_text": "Only invoice and warranty verification are supported.",
        }
    )
    return render(request, "core/pages/verify_document.html", context)
