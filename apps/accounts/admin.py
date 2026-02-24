from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, WarrantyClaim

admin.site.register(User, UserAdmin)


@admin.register(WarrantyClaim)
class WarrantyClaimAdmin(admin.ModelAdmin):
    list_display = ("claim_number", "user", "order", "product_name", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("claim_number", "warranty_card_number", "product_name", "user__username", "order__order_number")
