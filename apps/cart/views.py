from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from datetime import timedelta

from apps.products.models import Product, ProductVariant

from .models import CartItem, Coupon
from .services import get_or_create_cart


def cart_detail(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related("product", "variant")
    cart_product_ids = list(cart_items.values_list("product_id", flat=True))
    recommendations = Product.objects.filter(is_active=True).exclude(id__in=cart_product_ids).order_by("-is_featured", "-created_at")[:4]
    eta_from = timezone.localdate() + timedelta(days=3)
    eta_to = timezone.localdate() + timedelta(days=6)
    context = {
        "cart": cart,
        "cart_items": cart_items,
        "cart_item_count": sum(item.quantity for item in cart_items),
        "recommendations": recommendations,
        "eta_from": eta_from,
        "eta_to": eta_to,
    }
    return render(request, "cart/cart_detail.html", context)


@require_POST
def add_to_cart(request, product_id):
    cart = get_or_create_cart(request)
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    variant = None
    variant_id = request.POST.get("variant_id")
    if variant_id:
        variant = get_object_or_404(ProductVariant, pk=variant_id, product=product, is_active=True)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product, variant=variant)
    if not created:
        item.quantity += 1
    item.save()
    if created:
        messages.success(
            request,
            f"{product.name} cart me add ho gaya. Price lock rakhne ke liye checkout jaldi complete karein.",
            extra_tags="cart_reminder",
        )
    else:
        messages.warning(
            request,
            f"{product.name} pehle se cart me hai (Qty: {item.quantity}). Stock fast move ho raha hai, order jaldi place karein.",
            extra_tags="cart_reminder",
        )

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):
        return redirect(next_url)
    return redirect("cart:cart_detail")


@require_POST
def update_cart_item(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    qty = max(int(request.POST.get("quantity", 1)), 1)
    item.quantity = qty
    item.save(update_fields=["quantity"])
    return redirect("cart:cart_detail")


@require_POST
def remove_cart_item(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()
    return redirect("cart:cart_detail")


@require_POST
def apply_coupon(request):
    cart = get_or_create_cart(request)
    code = request.POST.get("code", "").strip().upper()
    coupon = Coupon.objects.filter(code=code, active=True).first()
    success = False
    message = "Invalid or expired coupon."
    if coupon and coupon.is_valid():
        cart.coupon = coupon
        cart.save(update_fields=["coupon"])
        success = True
        message = "Coupon applied successfully."

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "ok": success,
                "message": message,
                "subtotal": f"{cart.subtotal:.2f}",
                "discount": f"{cart.discount:.2f}",
                "gst": f"{cart.gst:.2f}",
                "grand_total": f"{cart.grand_total:.2f}",
            },
            status=200 if success else 400,
        )

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):
        return redirect(next_url)
    return redirect("cart:cart_detail")
