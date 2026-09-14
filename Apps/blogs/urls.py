from django.urls import path
from Apps.blogs import views

urlpatterns = [
    path("company/", views.company_detail, name="api-company-detail"),
    path("blogs/", views.blog_list, name="api-blog-list"),
    path("blogs/<slug:slug>/", views.blog_detail, name="api-blog-detail"),
    path("categories/", views.category_list, name="api-category-list"),
    path("tags/", views.tag_list, name="api-tag-list"),
]