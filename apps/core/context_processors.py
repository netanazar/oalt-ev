from django.conf import settings

from apps.cart.services import get_or_create_cart
from apps.products.models import Category


def global_settings(request):
    categories = Category.objects.filter(is_active=True).select_related("parent").order_by("parent__name", "name")
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
        cart = get_or_create_cart(request)
        cart_count = sum(item.quantity for item in cart.items.only("quantity"))
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

    return {
        "company_name": "Oalt EV Technology Pvt. Ltd.",
        "whatsapp_phone": digits or raw_phone,
        "whatsapp_phone_display": display_phone,
        "site_base_url": settings.SITE_BASE_URL,
        "nav_categories": categories,
        "cart_count": cart_count,
        "is_admin_console": is_admin_console,
    }
