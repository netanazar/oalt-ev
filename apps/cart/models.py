from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.functional import cached_property
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

    @cached_property
    def _line_items(self):
        if hasattr(self, "_prefetched_objects_cache") and "items" in self._prefetched_objects_cache:
            items = self._prefetched_objects_cache["items"]
            return list(items)
        return list(self.items.select_related("product", "variant"))

    @cached_property
    def _calculated_totals(self):
        gross = sum((item.line_total for item in self._line_items), Decimal("0.00"))
        gross = self._money(gross)
        if gross <= 0:
            subtotal = Decimal("0.00")
        else:
            subtotal = self._money(gross / self.GST_DIVISOR)

        discount = Decimal("0.00")
        if self.coupon and self.coupon.is_valid():
            discount = self._money((subtotal * Decimal(self.coupon.discount_percent)) / Decimal("100"))

        taxable = max(subtotal - discount, Decimal("0.00"))
        gst = self._money(taxable * self.GST_RATE)
        total = self._money(taxable + gst)
        return {
            "items_total": gross,
            "subtotal": subtotal,
            "discount": discount,
            "gst": gst,
            "grand_total": total,
        }

    @property
    def items_total(self) -> Decimal:
        return self._calculated_totals["items_total"]

    @property
    def subtotal(self) -> Decimal:
        return self._calculated_totals["subtotal"]

    @property
    def discount(self) -> Decimal:
        return self._calculated_totals["discount"]

    @property
    def gst(self) -> Decimal:
        return self._calculated_totals["gst"]

    @property
    def grand_total(self) -> Decimal:
        return self._calculated_totals["grand_total"]


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
