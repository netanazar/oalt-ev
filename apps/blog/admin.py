from django.contrib import admin

from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "published_at")
    list_filter = ("is_published", "published_at")
    search_fields = ("title", "excerpt", "content", "slug")
    ordering = ("-published_at",)
    readonly_fields = ("published_at",)
