from django.urls import path

from .views import checkout, download_invoice, order_confirmation

app_name = "orders"

urlpatterns = [
    path("checkout/", checkout, name="checkout"),
    path("confirmation/<str:order_number>/", order_confirmation, name="order_confirmation"),
    path("invoice/<str:order_number>/download/", download_invoice, name="download_invoice"),
]
