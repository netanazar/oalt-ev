from django.urls import path

from .views import apply

app_name = "dealership"

urlpatterns = [
    path("apply/", apply, name="apply"),
]
