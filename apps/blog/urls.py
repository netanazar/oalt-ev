from django.urls import path

from .views import blog_detail, blog_list

app_name = "blog"

urlpatterns = [
    path("", blog_list, name="list"),
    path("<slug:slug>/", blog_detail, name="detail"),
]
