from django.urls import path

from .views import compare_data_api, compare_options_api, product_detail, product_list, submit_emi_lead, submit_review

app_name = "products"

urlpatterns = [
    path("", product_list, name="product_list"),
    path("compare/options/", compare_options_api, name="compare_options_api"),
    path("compare/data/", compare_data_api, name="compare_data_api"),
    path("emi-lead/", submit_emi_lead, name="submit_emi_lead"),
    path("<slug:slug>/", product_detail, name="product_detail"),
    path("<slug:slug>/review/", submit_review, name="submit_review"),
]
