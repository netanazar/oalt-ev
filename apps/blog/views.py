from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import BlogPost


def blog_list(request):
    posts_qs = BlogPost.objects.filter(is_published=True).only(
        "title",
        "slug",
        "excerpt",
        "cover_image",
        "published_at",
    )
    page_obj = Paginator(posts_qs, 9).get_page(request.GET.get("page"))
    return render(
        request,
        "blog/list.html",
        {
            "posts": page_obj.object_list,
            "page_obj": page_obj,
        },
    )


def blog_detail(request, slug):
    post = get_object_or_404(
        BlogPost.objects.only("title", "slug", "excerpt", "content", "cover_image", "published_at"),
        slug=slug,
        is_published=True,
    )
    return render(request, "blog/detail.html", {"post": post})
