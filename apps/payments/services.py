from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from apps.orders.models import Order

from .models import Payment


def is_razorpay_available() -> bool:
    try:
        import razorpay  # noqa: F401
    except ImportError:
        return False
    return bool(getattr(settings, "RAZORPAY_KEY_ID", "")) and bool(getattr(settings, "RAZORPAY_KEY_SECRET", ""))


def _client():
    try:
        import razorpay
    except ImportError as exc:
        raise ImproperlyConfigured("Install razorpay package to enable payments.") from exc
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_razorpay_order(*, order: Order) -> dict:
    amount_paise = int(Decimal(order.total_amount) * 100)
    razorpay_order = _client().order.create(
        {"amount": amount_paise, "currency": settings.RAZORPAY_CURRENCY, "receipt": order.order_number, "payment_capture": 1}
    )
    Payment.objects.update_or_create(
        order=order,
        defaults={
            "provider_order_id": razorpay_order["id"],
            "amount": order.total_amount,
            "currency": settings.RAZORPAY_CURRENCY,
            "status": Payment.Status.CREATED,
            "raw_response": razorpay_order,
        },
    )
    return {"id": razorpay_order["id"], "amount": amount_paise, "currency": settings.RAZORPAY_CURRENCY, "key_id": settings.RAZORPAY_KEY_ID}


def verify_signature(*, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    try:
        import razorpay
    except ImportError:
        return False
    try:
        _client().utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )
        return True
    except razorpay.errors.SignatureVerificationError:
        return False


def refund_payment(*, payment: Payment, amount: Decimal | None = None):
    refund_amount = int((amount or payment.amount) * 100)
    response = _client().payment.refund(payment.provider_payment_id, {"amount": refund_amount})
    payment.status = Payment.Status.REFUNDED
    payment.raw_response = {"refund": response, "original": payment.raw_response}
    payment.save(update_fields=["status", "raw_response", "updated_at"])
    payment.order.status = Order.Status.CANCELLED
    payment.order.save(update_fields=["status", "updated_at"])
    return response
