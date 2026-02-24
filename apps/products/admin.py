from django.contrib import admin

from .models import Category, EmiLead, Product, ProductImage, ProductVariant, Review


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock", "is_active", "is_featured")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("category", "is_active", "is_featured")
    search_fields = ("name", "slug")
    inlines = [ProductImageInline, ProductVariantInline]


admin.site.register(Review)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "slug", "is_active", "created_at")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug", "parent__name")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(EmiLead)
class EmiLeadAdmin(admin.ModelAdmin):
    list_display = (
        "model_name",
        "customer_name",
        "customer_mobile",
        "customer_email",
        "unit_price",
        "quantity",
        "interest_rate",
        "selected_tenure_months",
        "created_at",
    )
    search_fields = ("model_name", "customer_name", "customer_mobile", "customer_email")
    list_filter = ("selected_tenure_months", "interest_rate", "created_at")
    readonly_fields = ("created_at",)
