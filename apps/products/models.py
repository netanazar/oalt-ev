from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=150, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["parent", "is_active"])]

    def clean(self):
        if self.parent_id and self.parent_id == self.id:
            raise ValidationError({"parent": "A category cannot be parent of itself."})

    @property
    def full_name(self) -> str:
        if not self.parent_id:
            return self.name
        names = [self.name]
        node = self.parent
        # Guard against cyclic relation from bad manual DB edits.
        visited = {self.id}
        while node and node.id not in visited:
            names.append(node.name)
            visited.add(node.id)
            node = node.parent
        return " > ".join(reversed(names))

    def __str__(self) -> str:
        return self.full_name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    short_description = models.CharField(max_length=350)
    description = models.TextField()
    technical_specifications = models.JSONField(default=dict, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    battery_capacity_kwh = models.DecimalField(max_digits=6, decimal_places=2)
    range_per_charge_km = models.PositiveIntegerField()
    stock = models.PositiveIntegerField(default=0)
    main_image = models.ImageField(upload_to="products/main/")
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "is_featured"]),
            models.Index(fields=["is_active", "created_at"]),
            models.Index(fields=["price"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

    @property
    def selling_price(self) -> Decimal:
        return self.discount_price if self.discount_price else self.price

    @property
    def rating(self):
        reviews = self.reviews.filter(is_approved=True)
        if not reviews.exists():
            return 0
        return round(sum(item.rating for item in reviews) / reviews.count(), 1)

    def get_absolute_url(self):
        return reverse("products:product_detail", kwargs={"slug": self.slug})

    @property
    def discount_percentage(self) -> int:
        if not self.discount_price or self.price <= 0:
            return 0
        discount = ((self.price - self.discount_price) / self.price) * Decimal("100")
        return max(int(discount.quantize(Decimal("1"))), 0)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products/gallery/")
    alt_text = models.CharField(max_length=150, blank=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.product.name} image"


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    color_name = models.CharField(max_length=80)
    color_code = models.CharField(max_length=7, help_text="Hex color code like #ffffff")
    image = models.ImageField(upload_to="products/variants/")
    stock = models.PositiveIntegerField(default=0)
    additional_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["product", "is_active"]), models.Index(fields=["color_name"])]
        unique_together = ("product", "color_name")

    def __str__(self) -> str:
        return f"{self.product.name} - {self.color_name}"

    @property
    def final_price(self):
        return self.product.selling_price + (self.additional_price or Decimal("0.00"))


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "is_approved"])]

    def __str__(self) -> str:
        return f"Review - {self.product.name}"


class EmiLead(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, related_name="emi_leads", null=True, blank=True)
    model_name = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    down_payment = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    selected_tenure_months = models.PositiveSmallIntegerField(default=12)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("12.00"))
    emi_chart = models.JSONField(default=dict, blank=True)
    customer_name = models.CharField(max_length=120)
    customer_mobile = models.CharField(max_length=20)
    customer_email = models.EmailField()
    source_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["customer_mobile", "created_at"]),
            models.Index(fields=["customer_email", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.model_name} EMI Lead - {self.customer_name}"
