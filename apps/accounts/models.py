from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta, date
from uuid import uuid4

from apps.orders.models import Order


def _safe_add_years(start_date: date, years: int) -> date:
    try:
        return start_date.replace(year=start_date.year + years)
    except ValueError:
        # Handles leap-day edge case (29 Feb -> 28 Feb)
        return start_date.replace(month=2, day=28, year=start_date.year + years)


class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["email"]), models.Index(fields=["username"])]


class WarrantyClaim(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RESOLVED = "resolved", "Resolved"

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="warranty_claims")
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="warranty_claims")
    claim_number = models.CharField(max_length=32, unique=True, db_index=True, editable=False)
    warranty_card_number = models.CharField(max_length=60)
    product_name = models.CharField(max_length=180)
    issue_description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.claim_number:
            stamp = timezone.now().strftime("%y%m%d%H%M%S")
            self.claim_number = f"WC-{stamp}-{uuid4().hex[:4].upper()}"
        super().save(*args, **kwargs)

    def delivery_reference_datetime(self):
        if self.order.status == Order.Status.DELIVERED:
            return self.order.updated_at
        return self.order.created_at

    def claim_deadline_datetime(self):
        return self.delivery_reference_datetime() + timedelta(days=7)

    def coverage_start_date(self) -> date:
        if self.created_at:
            return timezone.localtime(self.created_at).date()
        return timezone.localdate()

    def coverage_end_date(self) -> date:
        return _safe_add_years(self.coverage_start_date(), 2)

    def __str__(self):
        return self.claim_number
