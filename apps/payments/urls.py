from django.urls import path

from .views import razorpay_webhook, verify_payment

app_name = "payments"

urlpatterns = [
    path("verify/", verify_payment, name="verify_payment"),
    path("webhook/", razorpay_webhook, name="webhook"),
]
