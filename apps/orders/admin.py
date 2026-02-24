from django.contrib import admin
from django.utils.html import format_html, format_html_join

from .models import Order, OrderItem, ShippingAddress


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "product_image", "quantity", "price")
    readonly_fields = ("product_image",)
    autocomplete_fields = ("product",)

    def product_image(self, obj):
        if obj.product_id and getattr(obj.product, "main_image", None):
            return format_html(
                '<img src="{}" alt="{}" style="width:54px;height:54px;object-fit:cover;border-radius:8px;border:1px solid #e2e8f0;" />',
                obj.product.main_image.url,
                obj.product.name,
            )
        return "-"

    product_image.short_description = "Image"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "user",
        "products_preview",
        "status",
        "payment_method",
        "total_amount",
        "created_at",
    )
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("order_number", "user__username", "user__email")
    ordering = ("-created_at",)
    list_select_related = ("user",)
    inlines = (OrderItemInline,)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("user").prefetch_related("items__product")

    def products_preview(self, obj):
        all_items = list(obj.items.all())
        items = all_items[:3]
        if not all_items:
            return "-"
        lines = []
        for item in items:
            if item.product_id and getattr(item.product, "main_image", None):
                lines.append(
                    format_html(
                        '<div style="display:flex;align-items:center;gap:8px;white-space:nowrap;">'
                        '<img src="{}" alt="{}" style="width:28px;height:28px;object-fit:cover;border-radius:6px;border:1px solid #e2e8f0;" />'
                        '<span>{}</span>'
                        "</div>",
                        item.product.main_image.url,
                        item.product.name,
                        item.product.name,
                    )
                )
            else:
                lines.append(format_html("<div>{}</div>", item.product.name if item.product_id else "Unknown product"))
        extra_count = len(all_items) - len(items)
        if extra_count > 0:
            lines.append(format_html("<div style='font-size:11px;color:#475569;'>+{} more</div>", extra_count))
        return format_html_join("", "{}", ((line,) for line in lines))

    products_preview.short_description = "Products"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "quantity", "price")
    list_filter = ("order__status", "order__payment_method")
    search_fields = ("order__order_number", "product__name")
    list_select_related = ("order", "product")


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ("order", "full_name", "phone", "city", "state", "postal_code")
    search_fields = ("order__order_number", "full_name", "phone", "city", "state", "postal_code")
    list_select_related = ("order",)
