import json
import hmac
from hashlib import sha256

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.cart.services import get_or_create_cart
from apps.orders.models import Order

from .models import Payment, PaymentWebhookLog
from .services import verify_signature


@require_POST
def verify_payment(request):
    order_id = request.POST.get("order_id")
    rp_order_id = request.POST.get("razorpay_order_id")
    rp_payment_id = request.POST.get("razorpay_payment_id")
    rp_signature = request.POST.get("razorpay_signature")

    order = get_object_or_404(Order, pk=order_id, user=request.user)
    payment = get_object_or_404(Payment, order=order, provider_order_id=rp_order_id)

    is_valid = verify_signature(
        razorpay_order_id=rp_order_id,
        razorpay_payment_id=rp_payment_id,
        razorpay_signature=rp_signature,
    )
    if not is_valid:
        payment.status = Payment.Status.FAILED
        payment.failure_reason = "Signature verification failed"
        payment.save(update_fields=["status", "failure_reason", "updated_at"])
        return redirect("orders:order_confirmation", order_number=order.order_number)

    payment.provider_payment_id = rp_payment_id
    payment.provider_signature = rp_signature
    payment.status = Payment.Status.CAPTURED
    payment.save(update_fields=["provider_payment_id", "provider_signature", "status", "updated_at"])
    order.status = Order.Status.PAID
    order.save(update_fields=["status", "updated_at"])
    send_mail(
        "Order Payment Successful",
        f"Your payment for order {order.order_number} was successful.",
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        fail_silently=True,
    )
    cart = get_or_create_cart(request)
    cart.items.all().delete()
    cart.coupon = None
    cart.save(update_fields=["coupon", "updated_at"])
    return redirect("orders:order_confirmation", order_number=order.order_number)


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    signature = request.headers.get("X-Razorpay-Signature", "")
    body = request.body
    expected = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), body, sha256).hexdigest() if settings.RAZORPAY_WEBHOOK_SECRET else ""
    if not signature or not expected or not hmac.compare_digest(signature, expected):
        return JsonResponse({"ok": False}, status=400)
    payload = json.loads(body.decode("utf-8"))
    event = payload.get("event", "")
    event_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id", "")
    if event_id:
        PaymentWebhookLog.objects.get_or_create(
            event_id=event_id,
            defaults={"event_type": event, "payload": payload},
        )
    return HttpResponse(status=200)
