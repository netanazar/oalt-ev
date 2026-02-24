from django.db import transaction
from django.utils.crypto import get_random_string

from apps.cart.models import Cart

from .models import Order, OrderItem, ShippingAddress


def generate_order_number() -> str:
    return f"OALT-{get_random_string(10).upper()}"


@transaction.atomic
def create_order_from_cart(*, user, cart: Cart, address_data: dict, payment_method: str = Order.PaymentMethod.ONLINE) -> Order:
    order = Order.objects.create(
        user=user,
        order_number=generate_order_number(),
        payment_method=payment_method,
        subtotal=cart.subtotal,
        discount=cart.discount,
        gst=cart.gst,
        total_amount=cart.grand_total,
        coupon_code=cart.coupon.code if cart.coupon else "",
    )
    ShippingAddress.objects.create(order=order, **address_data)
    for item in cart.items.select_related("product", "variant", "variant__product"):
        OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity, price=item.unit_price)
    return order
