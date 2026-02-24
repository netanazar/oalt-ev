from django.contrib import admin

from .models import (
    HomeFeatureCard,
    HomeHeroSlide,
    HomeModeCard,
    HomeSectionConfig,
    ContactInquiry,
    NewsletterSubscriber,
    SiteContent,
    Testimonial,
)

admin.site.register(NewsletterSubscriber)


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("name", "designation", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "designation", "content")
    ordering = ("-created_at",)


@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    list_display = ("key", "title", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("key", "title", "subtitle")
    ordering = ("key",)


@admin.register(HomeHeroSlide)
class HomeHeroSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title",)
    ordering = ("order", "id")


@admin.register(HomeFeatureCard)
class HomeFeatureCardAdmin(admin.ModelAdmin):
    list_display = ("title", "card_type", "order", "is_active")
    list_filter = ("is_active", "card_type")
    search_fields = ("title",)
    ordering = ("order", "id")


@admin.register(HomeModeCard)
class HomeModeCardAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title",)
    ordering = ("order", "id")


@admin.register(HomeSectionConfig)
class HomeSectionConfigAdmin(admin.ModelAdmin):
    list_display = ("key", "heading", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("key", "heading")


@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "created_at")
    search_fields = ("name", "email", "subject")
    list_filter = ("created_at",)
