from django.contrib import admin

from .models import Payment, PaymentWebhookLog

admin.site.register(Payment)
admin.site.register(PaymentWebhookLog)
