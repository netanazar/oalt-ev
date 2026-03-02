from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import timedelta

from apps.cart.services import get_or_create_cart
from apps.payments.services import create_razorpay_order, is_razorpay_available

from .forms import CheckoutAddressForm
from .models import Order
from .pdf import build_invoice_pdf
from .services import create_order_from_cart


@login_required
def checkout(request):
    cart = get_or_create_cart(request)
    cart_items = list(cart.items.select_related("product", "variant"))
    cart._prefetched_objects_cache = {"items": cart_items}
    gateway_ready = is_razorpay_available()
    eta_from = timezone.localdate() + timedelta(days=2)
    eta_to = timezone.localdate() + timedelta(days=5)
    payment_method_preview = "Choose between Online Payment and Cash on Delivery."
    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect("cart:cart_detail")

    if request.method == "POST":
        form = CheckoutAddressForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data.copy()
            payment_method = cleaned_data.pop("payment_method", Order.PaymentMethod.ONLINE)
            if payment_method == Order.PaymentMethod.ONLINE and not gateway_ready:
                messages.error(request, "Online payment gateway is temporarily unavailable. Please select Cash on Delivery.")
                return redirect("orders:checkout")

            order = create_order_from_cart(
                user=request.user,
                cart=cart,
                address_data=cleaned_data,
                payment_method=payment_method,
            )

            if payment_method == Order.PaymentMethod.COD:
                cart.items.all().delete()
                cart.coupon = None
                cart.save(update_fields=["coupon", "updated_at"])
                messages.success(request, "Order placed successfully with Cash on Delivery.")
                return redirect("orders:order_confirmation", order_number=order.order_number)

            try:
                rp_order = create_razorpay_order(order=order)
            except ImproperlyConfigured:
                messages.error(request, "Payment gateway is not configured. Please try again after setup.")
                return redirect("orders:checkout")
            return render(
                request,
                "orders/payment.html",
                {"order": order, "razorpay_order": rp_order, "razorpay_key_id": rp_order["key_id"]},
            )
    else:
        form = CheckoutAddressForm(
            initial={
                "email": request.user.email,
                "phone": request.user.phone,
                "payment_method": Order.PaymentMethod.ONLINE if gateway_ready else Order.PaymentMethod.COD,
            }
        )
    return render(
        request,
        "orders/checkout.html",
        {
            "cart": cart,
            "cart_items": cart_items,
            "form": form,
            "gateway_ready": gateway_ready,
            "eta_from": eta_from,
            "eta_to": eta_to,
            "payment_method_preview": payment_method_preview,
        },
    )


@login_required
def order_confirmation(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, "orders/confirmation.html", {"order": order})


@login_required
def download_invoice(request, order_number):
    order = (
        Order.objects.filter(order_number=order_number, user=request.user)
        .select_related("shipping_address", "user")
        .prefetch_related("items", "items__product")
        .first()
    )
    if not order:
        messages.error(request, "Order not found.")
        return redirect("accounts:dashboard")

    if order.status != Order.Status.DELIVERED:
        messages.warning(request, "Invoice will be available after order is delivered.")
        return redirect("accounts:dashboard")

    pdf_bytes = build_invoice_pdf(order=order, generated_at=timezone.localtime())
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice-{order.order_number}.pdf"'
    return response
