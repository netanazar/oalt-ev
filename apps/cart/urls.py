from django.urls import path

from .views import add_to_cart, apply_coupon, cart_detail, remove_cart_item, update_cart_item

app_name = "cart"

urlpatterns = [
    path("", cart_detail, name="cart_detail"),
    path("add/<int:product_id>/", add_to_cart, name="add_to_cart"),
    path("update/<int:item_id>/", update_cart_item, name="update_cart_item"),
    path("remove/<int:item_id>/", remove_cart_item, name="remove_cart_item"),
    path("coupon/", apply_coupon, name="apply_coupon"),
]
