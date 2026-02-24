import json
from decimal import Decimal, InvalidOperation
from urllib.parse import quote_plus
from urllib import request as urllib_request
from urllib.error import URLError

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Max, Min, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ReviewForm
from .models import Category, EmiLead, Product


def product_list(request):
    active_categories = Category.objects.filter(is_active=True).select_related("parent")
    category_tree = (
        active_categories.filter(parent__isnull=True)
        .prefetch_related(Prefetch("children", queryset=Category.objects.filter(is_active=True).order_by("name")))
        .order_by("name")
    )
    base_qs = Product.objects.filter(is_active=True).select_related("category")
    products = base_qs
    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()
    price_min = request.GET.get("price__gte")
    price_max = request.GET.get("price__lte")
    battery_min = request.GET.get("battery__gte")
    battery_max = request.GET.get("battery__lte")
    range_min = request.GET.get("range__gte")
    range_max = request.GET.get("range__lte")
    discount_only = request.GET.get("discount") == "1"
    in_stock_only = request.GET.get("in_stock") == "1"
    featured_only = request.GET.get("featured") == "1"

    if query:
        products = products.filter(name__icontains=query)
    if category_id.isdigit():
        selected_category = active_categories.filter(id=int(category_id)).first()
        if selected_category:
            if selected_category.parent_id:
                products = products.filter(category_id=selected_category.id)
            else:
                child_ids = list(selected_category.children.filter(is_active=True).values_list("id", flat=True))
                products = products.filter(category_id__in=[selected_category.id, *child_ids])
    if price_min:
        products = products.filter(price__gte=price_min)
    if price_max:
        products = products.filter(price__lte=price_max)
    if battery_min:
        products = products.filter(battery_capacity_kwh__gte=battery_min)
    if battery_max:
        products = products.filter(battery_capacity_kwh__lte=battery_max)
    if range_min:
        products = products.filter(range_per_charge_km__gte=range_min)
    if range_max:
        products = products.filter(range_per_charge_km__lte=range_max)
    if discount_only:
        products = products.filter(discount_price__isnull=False)
    if in_stock_only:
        products = products.filter(stock__gt=0)
    if featured_only:
        products = products.filter(is_featured=True)

    sort = request.GET.get("sort", "latest")
    sort_map = {
        "latest": "-created_at",
        "price_low_high": "price",
        "price_high_low": "-price",
        "name_az": "name",
        "range_high_low": "-range_per_charge_km",
        "battery_high_low": "-battery_capacity_kwh",
    }
    products = products.order_by(sort_map.get(sort, "-created_at"))
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)

    summary = base_qs.aggregate(
        min_price=Min("price"),
        max_price=Max("price"),
        min_battery=Min("battery_capacity_kwh"),
        max_battery=Max("battery_capacity_kwh"),
        min_range=Min("range_per_charge_km"),
        max_range=Max("range_per_charge_km"),
    )

    recent_ids = request.session.get("recent_viewed_products", [])
    recent_lookup = Product.objects.filter(is_active=True, pk__in=recent_ids).select_related("category")
    recent_map = {item.pk: item for item in recent_lookup}
    recent_viewed_products = [recent_map[pid] for pid in recent_ids if pid in recent_map][:8]

    return render(
        request,
        "products/product_list.html",
        {
            "page_obj": page_obj,
            "products": page_obj.object_list,
            "search_query": query,
            "selected_category": category_id,
            "selected_sort": sort,
            "selected_discount": discount_only,
            "selected_in_stock": in_stock_only,
            "selected_featured": featured_only,
            "categories": active_categories.order_by("name"),
            "category_tree": category_tree,
            "summary": summary,
            "recent_viewed_products": recent_viewed_products,
            "querystring": query_params.urlencode(),
        },
    )


def compare_options_api(request):
    exclude_id = request.GET.get("exclude", "").strip()
    search_query = request.GET.get("q", "").strip()

    products = Product.objects.filter(is_active=True).select_related("category").order_by("-is_featured", "-created_at")
    if exclude_id.isdigit():
        products = products.exclude(pk=int(exclude_id))
    if search_query:
        products = products.filter(name__icontains=search_query)
    products = products[:24]

    results = []
    for item in products:
        results.append(
            {
                "id": item.id,
                "name": item.name,
                "category": item.category.name,
                "price": float(item.selling_price),
                "range_km": item.range_per_charge_km,
                "battery_kwh": float(item.battery_capacity_kwh),
                "image_url": item.main_image.url if item.main_image else "",
                "product_url": item.get_absolute_url(),
            }
        )

    return JsonResponse({"ok": True, "results": results})


def compare_data_api(request):
    ids_param = request.GET.get("ids", "").strip()
    selected_ids = [int(x) for x in ids_param.split(",") if x.strip().isdigit()][:4]
    if len(selected_ids) < 2:
        return JsonResponse({"ok": False, "error": "Please select at least 2 products for compare."}, status=400)

    products_qs = Product.objects.filter(is_active=True, pk__in=selected_ids).select_related("category")
    products_map = {item.pk: item for item in products_qs}
    products = [products_map[pid] for pid in selected_ids if pid in products_map]
    if len(products) < 2:
        return JsonResponse({"ok": False, "error": "Selected products are unavailable."}, status=404)

    all_spec_keys = []
    for product in products:
        for key in product.technical_specifications.keys():
            if key not in all_spec_keys:
                all_spec_keys.append(key)

    rows = [
        {
            "label": "Price",
            "values": [f"{p.selling_price:.2f}" for p in products],
            "is_currency": True,
        },
        {
            "label": "Category",
            "values": [p.category.name for p in products],
            "is_currency": False,
        },
        {
            "label": "Battery Capacity",
            "values": [f"{p.battery_capacity_kwh} kWh" for p in products],
            "is_currency": False,
        },
        {
            "label": "Range Per Charge",
            "values": [f"{p.range_per_charge_km} km" for p in products],
            "is_currency": False,
        },
        {
            "label": "Stock",
            "values": [("In Stock" if p.stock > 0 else "Out of Stock") for p in products],
            "is_currency": False,
        },
        {
            "label": "Rating",
            "values": [f"{p.rating}/5" for p in products],
            "is_currency": False,
        },
    ]

    for key in all_spec_keys:
        rows.append(
            {
                "label": key,
                "values": [str(p.technical_specifications.get(key, "-")) for p in products],
                "is_currency": False,
            }
        )

    products_payload = [
        {
            "id": p.id,
            "name": p.name,
            "url": p.get_absolute_url(),
            "image_url": p.main_image.url if p.main_image else "",
            "price": float(p.selling_price),
        }
        for p in products
    ]
    return JsonResponse({"ok": True, "products": products_payload, "rows": rows})


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.prefetch_related("images", "reviews", "variants"), slug=slug, is_active=True)
    review_form = ReviewForm()
    related_products = (
        Product.objects.filter(is_active=True, category=product.category)
        .exclude(pk=product.pk)
        .order_by("-is_featured", "-created_at")[:12]
    )
    if not related_products.exists():
        related_products = Product.objects.filter(is_active=True).exclude(pk=product.pk).order_by("-created_at")[:12]
    frequently_bought = list(related_products[:2])
    bundle_total = product.selling_price + sum((item.selling_price for item in frequently_bought), Decimal("0"))

    approved_reviews = product.reviews.filter(is_approved=True)
    review_count = approved_reviews.count()
    about_points = [line.strip("- ").strip() for line in product.description.splitlines() if line.strip()]
    if not about_points:
        about_points = [product.short_description]
    long_description = product.description.strip()
    overview_paragraphs = [p.strip() for p in long_description.splitlines() if p.strip()]
    if not overview_paragraphs:
        overview_paragraphs = [product.short_description]

    specs = list(product.technical_specifications.items())
    split_index = (len(specs) + 1) // 2
    technical_specs_left = specs[:split_index]
    technical_specs_right = specs[split_index:]

    active_variants = [v for v in product.variants.all() if v.is_active]
    requested_variant_id = request.GET.get("variant", "").strip()
    selected_variant = active_variants[0] if active_variants else None
    if requested_variant_id.isdigit():
        requested_variant = next((v for v in active_variants if v.id == int(requested_variant_id)), None)
        if requested_variant:
            selected_variant = requested_variant

    context = {
        "product": product,
        "review_form": review_form,
        "related_products": related_products,
        "approved_reviews": approved_reviews,
        "review_count": review_count,
        "about_points": about_points,
        "overview_paragraphs": overview_paragraphs,
        "technical_specs_left": technical_specs_left,
        "technical_specs_right": technical_specs_right,
        "frequently_bought": frequently_bought,
        "bundle_total": bundle_total,
    }
    context["variants"] = active_variants
    context["selected_variant"] = selected_variant
    context["shipping_terms"] = [
        "Dispatch within 24-48 hours from nearest Oalt EV warehouse.",
        "Pre-delivery quality check and secure packaging included.",
        "Estimated delivery 3-7 business days depending on PIN code.",
        "Free replacement support for manufacturing defect claims as per policy.",
    ]
    context["faq_items"] = [
        {
            "q": "Is this cycle ready to ride after delivery?",
            "a": "Most units come 90% pre-assembled. Basic setup guidance is provided in the box.",
        },
        {
            "q": "Can I use it without battery assist?",
            "a": "Yes. You can ride in pedal-only mode and switch assist levels anytime.",
        },
        {
            "q": "How often should I service it?",
            "a": "We recommend a quick check every 3 months and a full service every 6 months.",
        },
        {
            "q": "Is battery replacement available later?",
            "a": "Yes, official battery replacements are available through authorized support.",
        },
    ]

    share_url = request.build_absolute_uri(product.get_absolute_url())
    share_text = f"Check out {product.name} by Oalt EV"
    context["product_share_url"] = share_url
    context["share_links"] = {
        "whatsapp": f"https://wa.me/?text={quote_plus(f'{share_text} {share_url}')}",
        "facebook": f"https://www.facebook.com/sharer/sharer.php?u={quote_plus(share_url)}",
        "x": f"https://twitter.com/intent/tweet?text={quote_plus(share_text)}&url={quote_plus(share_url)}",
        "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={quote_plus(share_url)}",
        "email": f"mailto:?subject={quote_plus(share_text)}&body={quote_plus(share_url)}",
    }

    recent_ids = request.session.get("recent_viewed_products", [])
    filtered_ids = [pid for pid in recent_ids if pid != product.id]
    recent_lookup = Product.objects.filter(is_active=True, pk__in=filtered_ids).select_related("category")
    recent_map = {item.pk: item for item in recent_lookup}
    context["recent_viewed_products"] = [recent_map[pid] for pid in filtered_ids if pid in recent_map][:8]

    new_recent = [product.id] + [pid for pid in recent_ids if pid != product.id]
    request.session["recent_viewed_products"] = new_recent[:20]
    request.session.modified = True

    return render(request, "products/product_detail.html", context)


def _sales_team_emails():
    configured = [item.strip() for item in getattr(settings, "SALES_TEAM_EMAILS", []) if item.strip()]
    if configured:
        return configured
    return [settings.DEFAULT_FROM_EMAIL]


def _sales_team_whatsapp_numbers():
    configured = [item.strip() for item in getattr(settings, "SALES_TEAM_WHATSAPP_NUMBERS", []) if item.strip()]
    if configured:
        return configured
    fallback = getattr(settings, "WHATSAPP_PHONE", "").strip()
    return [fallback] if fallback else []


def _send_whatsapp_message(phone_number: str, message: str):
    api_url = getattr(settings, "WHATSAPP_API_URL", "").strip()
    if not api_url or not phone_number:
        return False
    payload = json.dumps(
        {
            "to": phone_number,
            "message": message,
            "token": getattr(settings, "WHATSAPP_API_TOKEN", ""),
        }
    ).encode("utf-8")
    req = urllib_request.Request(api_url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib_request.urlopen(req, timeout=8):
            return True
    except (URLError, ValueError):
        return False


@require_POST
def submit_emi_lead(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "Invalid payload."}, status=400)

    model_name = str(payload.get("model_name", "")).strip()
    customer_name = str(payload.get("customer_name", "")).strip()
    customer_mobile = str(payload.get("customer_mobile", "")).strip()
    customer_email = str(payload.get("customer_email", "")).strip().lower()
    source_url = str(payload.get("source_url", "")).strip()
    emi_chart = payload.get("emi_chart", {})
    product_id = str(payload.get("product_id", "")).strip()

    if not model_name or not customer_name or not customer_email or not customer_mobile:
        return JsonResponse({"ok": False, "error": "Please fill all required fields."}, status=400)
    if "@" not in customer_email:
        return JsonResponse({"ok": False, "error": "Please enter valid email id."}, status=400)
    if len("".join(ch for ch in customer_mobile if ch.isdigit())) < 10:
        return JsonResponse({"ok": False, "error": "Please enter valid mobile number."}, status=400)

    try:
        unit_price = Decimal(str(payload.get("unit_price", "0")))
        down_payment = Decimal(str(payload.get("down_payment", "0")))
        interest_rate = Decimal(str(payload.get("interest_rate", "12")))
        quantity = max(int(payload.get("quantity", 1)), 1)
        selected_tenure_months = int(payload.get("selected_tenure_months", 12))
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Invalid EMI values."}, status=400)

    if selected_tenure_months not in {6, 9, 12, 18, 24}:
        selected_tenure_months = 12
    if interest_rate not in {Decimal("9"), Decimal("12"), Decimal("15"), Decimal("18")}:
        interest_rate = Decimal("12")

    product = None
    if product_id.isdigit():
        product = Product.objects.filter(pk=int(product_id), is_active=True).first()

    lead = EmiLead.objects.create(
        product=product,
        model_name=model_name,
        unit_price=unit_price,
        quantity=quantity,
        down_payment=down_payment,
        selected_tenure_months=selected_tenure_months,
        interest_rate=interest_rate,
        emi_chart=emi_chart if isinstance(emi_chart, dict) else {},
        customer_name=customer_name,
        customer_mobile=customer_mobile,
        customer_email=customer_email,
        source_url=source_url,
    )

    summary_lines = [
        f"EMI Lead ID: {lead.id}",
        f"Model: {lead.model_name}",
        f"Unit Price: ₹ {lead.unit_price}",
        f"Quantity: {lead.quantity}",
        f"Down Payment: ₹ {lead.down_payment}",
        f"Interest: {lead.interest_rate}%",
        f"Selected Tenure: {lead.selected_tenure_months} months",
        f"Customer: {lead.customer_name}",
        f"Mobile: {lead.customer_mobile}",
        f"Email: {lead.customer_email}",
        f"Source: {lead.source_url or '-'}",
    ]
    summary_text = "\n".join(summary_lines)

    sales_subject = f"New EMI Lead - {lead.model_name}"
    send_mail(
        subject=sales_subject,
        message=summary_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=_sales_team_emails(),
        fail_silently=True,
    )
    send_mail(
        subject=f"EMI Request Received - {lead.model_name}",
        message=(
            f"Hi {lead.customer_name},\n\n"
            "Thanks for your EMI request. Our team will share your personalized deal shortly.\n\n"
            f"Model: {lead.model_name}\n"
            f"Reference ID: {lead.id}\n\n"
            "Regards,\nOalt EV Sales Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[lead.customer_email],
        fail_silently=True,
    )

    whatsapp_text = (
        f"New EMI Lead%0A"
        f"ID: {lead.id}%0A"
        f"Model: {lead.model_name}%0A"
        f"Price: ₹ {lead.unit_price}%0A"
        f"Qty: {lead.quantity}%0A"
        f"Customer: {lead.customer_name}%0A"
        f"Mobile: {lead.customer_mobile}%0A"
        f"Email: {lead.customer_email}"
    )
    sales_wa_links = [f"https://wa.me/{num}?text={whatsapp_text}" for num in _sales_team_whatsapp_numbers()]

    # Optional direct delivery via configured WhatsApp API.
    for number in _sales_team_whatsapp_numbers():
        _send_whatsapp_message(number, summary_text)
    _send_whatsapp_message(lead.customer_mobile, f"Your EMI request (ID {lead.id}) has been received by Oalt EV.")

    return JsonResponse(
        {
            "ok": True,
            "message": "EMI request submitted successfully.",
            "sales_whatsapp_links": sales_wa_links,
        }
    )


@login_required
def submit_review(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.product = product
        review.save()
        messages.success(request, "Review submitted for moderation.")
    else:
        messages.error(request, "Unable to submit review.")
    return redirect(product.get_absolute_url())

