from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum
from django.urls import reverse
from urllib.parse import urlencode

from apps.cart.models import Cart, CartItem
from apps.products.models import Category


def _normalize_text(value: str) -> str:
    return "".join(ch for ch in (value or "").lower() if ch.isalnum())


def _find_category(categories, aliases, used_ids=None):
    used_ids = used_ids or set()
    normalized_aliases = [_normalize_text(alias) for alias in aliases if alias]
    for category in categories:
        if category.id in used_ids:
            continue
        haystack = f"{category.name} {category.slug}"
        normalized_haystack = _normalize_text(haystack)
        for alias in normalized_aliases:
            if alias and alias in normalized_haystack:
                return category
    return None


def _category_url(base_url: str, category, fallback_query: str = "") -> str:
    if category:
        return f"{base_url}?{urlencode({'category': category.id})}"
    if fallback_query:
        return f"{base_url}?{urlencode({'q': fallback_query})}"
    return base_url


def global_settings(request):
    cache_timeout = getattr(settings, "CACHE_TTL", 900)
    categories = cache.get("global_nav_categories")
    if categories is None:
        categories = list(
            Category.objects.filter(is_active=True).select_related("parent").order_by("parent__name", "name")
        )
        cache.set("global_nav_categories", categories, cache_timeout)

    raw_phone = str(settings.WHATSAPP_PHONE or "").strip()
    digits = "".join(ch for ch in raw_phone if ch.isdigit())
    if digits.startswith("91") and len(digits) >= 12:
        display_phone = f"+91 {digits[2:12]}"
    elif len(digits) == 10:
        display_phone = f"+91 {digits}"
    else:
        display_phone = raw_phone

    cart_count = 0
    try:
        cart_id = None
        if request.user.is_authenticated:
            cart_id = Cart.objects.filter(user=request.user).values_list("id", flat=True).first()
        elif request.session.session_key:
            cart_id = Cart.objects.filter(session_key=request.session.session_key).values_list("id", flat=True).first()

        if cart_id:
            cart_count = (
                CartItem.objects.filter(cart_id=cart_id).aggregate(total_qty=Sum("quantity")).get("total_qty") or 0
            )
    except Exception:
        cart_count = 0

    resolver = getattr(request, "resolver_match", None)
    namespace = getattr(resolver, "namespace", "") if resolver else ""
    url_name = getattr(resolver, "url_name", "") if resolver else ""
    is_admin_console = bool(
        request.user.is_authenticated
        and request.user.is_staff
        and namespace == "core"
        and url_name in {"dashboard", "dashboard_manage"}
    )

    product_list_url = reverse("products:product_list")
    used_category_ids = set()

    all_bikes_parent = _find_category(
        categories,
        aliases=("all bikes", "all bikes category", "all bikes parent", "allbike"),
        used_ids=used_category_ids,
    )
    if all_bikes_parent:
        used_category_ids.add(all_bikes_parent.id)

    lithium_parent = _find_category(
        categories,
        aliases=("lithium ion battery pack", "lithium-ion battery pack", "battery pack"),
        used_ids=used_category_ids,
    )
    if lithium_parent:
        used_category_ids.add(lithium_parent.id)

    ev_conversion_parent = _find_category(
        categories,
        aliases=("ev conversion kit", "ev conversion", "conversion kit"),
        used_ids=used_category_ids,
    )
    if ev_conversion_parent:
        used_category_ids.add(ev_conversion_parent.id)

    def build_child(label, aliases):
        matched_category = _find_category(categories, aliases=aliases, used_ids=used_category_ids)
        if matched_category:
            used_category_ids.add(matched_category.id)
        return {
            "name": label,
            "url": _category_url(product_list_url, matched_category, fallback_query=label),
        }

    nav_main_categories = [
        {
            "title": "All Bikes",
            "url": _category_url(product_list_url, all_bikes_parent, fallback_query="All Bikes"),
            "children": [
                build_child("Sprint", ("oalt sprint", "sprint")),
                build_child("Aspire", ("oalt aspire", "aspire")),
                build_child("Ignite", ("oalt ignite", "ignite")),
                build_child("E-Tricycle", ("e-tricycle", "etricycle", "tricycle")),
                build_child("E-Wheelchair", ("e-wheelchair", "ewheelchair", "wheelchair")),
            ],
        },
        {
            "title": "Lithium-ion Battery Pack",
            "url": _category_url(product_list_url, lithium_parent, fallback_query="Lithium-ion Battery Pack"),
            "children": [
                build_child("2 Wheeler", ("2 wheeler", "2wheeler", "two wheeler", "two-wheeler")),
                build_child("3 Wheeler", ("3 wheeler", "3wheeler", "three wheeler", "three-wheeler")),
            ],
        },
        {
            "title": "EV Conversion Kit",
            "url": _category_url(product_list_url, ev_conversion_parent, fallback_query="EV Conversion Kit"),
            "children": [],
        },
    ]

    return {
        "company_name": "Oalt EV Technology Pvt. Ltd.",
        "whatsapp_phone": digits or raw_phone,
        "whatsapp_phone_display": display_phone,
        "current_city": (request.session.get("current_city") or "India"),
        "current_pincode": (request.session.get("current_pincode") or ""),
        "site_base_url": settings.SITE_BASE_URL,
        "tailwind_cdn_enabled": getattr(settings, "TAILWIND_CDN_ENABLED", True),
        "font_awesome_cdn_enabled": getattr(settings, "FONT_AWESOME_CDN_ENABLED", True),
        "nav_categories": categories,
        "nav_main_categories": nav_main_categories,
        "cart_count": cart_count,
        "is_admin_console": is_admin_console,
    }
