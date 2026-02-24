from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.products.models import Product


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return [
            "core:home",
            "products:product_list",
            "dealership:apply",
            "core:about_us",
            "core:contact_us",
            "core:privacy_policy",
            "core:terms_conditions",
            "core:return_refund",
            "core:shipping_terms",
            "core:disclaimer",
            "core:cancellation_policy",
            "core:warranty_policy",
            "core:faq",
            "core:cookies_policy",
        ]

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Product.objects.filter(is_active=True).only("slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at
