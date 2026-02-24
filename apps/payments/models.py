from django.db import models

from apps.orders.models import Order


class Payment(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        AUTHORIZED = "authorized", "Authorized"
        CAPTURED = "captured", "Captured"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    provider = models.CharField(max_length=20, default="razorpay")
    provider_order_id = models.CharField(max_length=80, blank=True)
    provider_payment_id = models.CharField(max_length=80, blank=True)
    provider_signature = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    failure_reason = models.TextField(blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["provider_order_id", "provider_payment_id", "status"])]

    def __str__(self) -> str:
        return f"{self.order.order_number} - {self.status}"


class PaymentWebhookLog(models.Model):
    event_id = models.CharField(max_length=120, unique=True)
    event_type = models.CharField(max_length=120)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.event_type
