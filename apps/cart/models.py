from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.products.models import Product, ProductVariant


class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    discount_percent = models.PositiveSmallIntegerField()
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(default=1000)

    class Meta:
        indexes = [models.Index(fields=["code", "active"])]

    def __str__(self) -> str:
        return self.code

    def is_valid(self) -> bool:
        now = timezone.now()
        return self.active and self.valid_from <= now <= self.valid_to


class Cart(models.Model):
    GST_RATE = Decimal("0.18")
    GST_DIVISOR = Decimal("1.18")

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart", null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["session_key"])]

    def __str__(self) -> str:
        return f"Cart {self.pk}"

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))

    @property
    def items_total(self) -> Decimal:
        # Item prices are stored and shown as GST-inclusive totals.
        gross = sum((item.line_total for item in self.items.select_related("product", "variant")), Decimal("0.00"))
        return self._money(gross)

    @property
    def subtotal(self) -> Decimal:
        # Subtotal in order summary should be GST-exclusive.
        if self.items_total <= 0:
            return Decimal("0.00")
        return self._money(self.items_total / self.GST_DIVISOR)

    @property
    def discount(self) -> Decimal:
        if self.coupon and self.coupon.is_valid():
            value = (self.subtotal * Decimal(self.coupon.discount_percent)) / Decimal("100")
            return self._money(value)
        return Decimal("0.00")

    @property
    def gst(self) -> Decimal:
        taxable = max(self.subtotal - self.discount, Decimal("0.00"))
        return self._money(taxable * self.GST_RATE)

    @property
    def grand_total(self) -> Decimal:
        taxable = max(self.subtotal - self.discount, Decimal("0.00"))
        return self._money(taxable + self.gst)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "product", "variant")
        indexes = [models.Index(fields=["cart", "product", "variant"])]

    @property
    def unit_price(self) -> Decimal:
        if self.variant:
            return self.variant.final_price
        return self.product.selling_price

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity
