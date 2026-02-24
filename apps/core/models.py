from django.db import models


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email"])]

    def __str__(self) -> str:
        return self.email


class Testimonial(models.Model):
    name = models.CharField(max_length=120)
    designation = models.CharField(max_length=120, blank=True)
    image = models.ImageField(upload_to="home/testimonials/", blank=True, null=True)
    content = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class SiteContent(models.Model):
    key = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    subtitle = models.TextField(blank=True)
    image = models.ImageField(upload_to="site-content/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Content"
        verbose_name_plural = "Site Contents"

    def __str__(self) -> str:
        return self.key


class HomeHeroSlide(models.Model):
    title = models.CharField(max_length=220)
    subtitle = models.TextField(blank=True)
    cta_text = models.CharField(max_length=80, blank=True)
    cta_url = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to="home/hero/")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        indexes = [models.Index(fields=["is_active", "order"])]

    def __str__(self) -> str:
        return self.title


class HomeFeatureCard(models.Model):
    class CardType(models.TextChoices):
        LARGE = "large", "Large"
        SMALL = "small", "Small"

    title = models.CharField(max_length=180)
    description = models.CharField(max_length=280, blank=True)
    image = models.ImageField(upload_to="home/features/")
    card_type = models.CharField(max_length=12, choices=CardType.choices, default=CardType.SMALL)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        indexes = [models.Index(fields=["is_active", "card_type", "order"])]

    def __str__(self) -> str:
        return self.title


class HomeModeCard(models.Model):
    title = models.CharField(max_length=140)
    description = models.CharField(max_length=220)
    image = models.ImageField(upload_to="home/modes/")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        indexes = [models.Index(fields=["is_active", "order"])]

    def __str__(self) -> str:
        return self.title


class HomeSectionConfig(models.Model):
    key = models.CharField(max_length=80, unique=True)
    heading = models.CharField(max_length=220)
    subheading = models.TextField(blank=True)
    cta_text = models.CharField(max_length=80, blank=True)
    cta_url = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to="home/sections/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key


class ContactInquiry(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=180)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email", "created_at"])]

    def __str__(self) -> str:
        return f"{self.name} - {self.subject}"
