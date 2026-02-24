from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.core.sitemaps import ProductSitemap, StaticViewSitemap

sitemaps = {
    "static": StaticViewSitemap,
    "products": ProductSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("shop/", include("apps.products.urls")),
    path("cart/", include("apps.cart.urls")),
    path("orders/", include("apps.orders.urls")),
    path("payments/", include("apps.payments.urls")),
    path("dealership/", include("apps.dealership.urls")),
    path("blog/", include("apps.blog.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
]

if getattr(settings, "SOCIAL_AUTH_AVAILABLE", False):
    urlpatterns += [
        path("accounts/social/", include("allauth.urls")),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
