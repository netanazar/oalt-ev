from django.urls import path

from .views import (
    HomeView,
    about_us,
    contact_us,
    dashboard,
    dashboard_export_report,
    dashboard_manage,
    legal_page,
    newsletter_subscribe,
    verify_document,
)

app_name = "core"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("about-us/", about_us, name="about_us"),
    path("contact-us/", contact_us, name="contact_us"),
    path("privacy-policy/", legal_page, {"slug": "privacy-policy"}, name="privacy_policy"),
    path("terms-conditions/", legal_page, {"slug": "terms-conditions"}, name="terms_conditions"),
    path("return-refund/", legal_page, {"slug": "return-refund"}, name="return_refund"),
    path("shipping-terms/", legal_page, {"slug": "shipping-terms"}, name="shipping_terms"),
    path("disclaimer/", legal_page, {"slug": "disclaimer"}, name="disclaimer"),
    path("cancellation-policy/", legal_page, {"slug": "cancellation-policy"}, name="cancellation_policy"),
    path("warranty-policy/", legal_page, {"slug": "warranty-policy"}, name="warranty_policy"),
    path("faq/", legal_page, {"slug": "faq"}, name="faq"),
    path("cookies-policy/", legal_page, {"slug": "cookies-policy"}, name="cookies_policy"),
    path("verify-document/", verify_document, name="verify_document"),
    path("newsletter/subscribe/", newsletter_subscribe, name="newsletter_subscribe"),
    path("dashboard/", dashboard, name="dashboard"),
    path("dashboard/manage/<str:section>/", dashboard_manage, name="dashboard_manage"),
    path("dashboard/reports/<str:report_type>/export/", dashboard_export_report, name="dashboard_export_report"),
]
