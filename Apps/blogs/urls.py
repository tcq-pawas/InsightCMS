from django.urls import path
from Apps.blogs import views
from Apps.blogs.views import (
    dashboard_blog_create,
    dashboard_blog_edit,
    dashboard_blog_toggle_publish,
    dashboard_blog_delete,
)

urlpatterns = [
    path('blogs/create/', dashboard_blog_create, name='dashboard_blog_create'),
    path('blogs/<int:page_id>/edit/', dashboard_blog_edit, name='dashboard_blog_edit'),
    path('blogs/<int:page_id>/toggle-publish/', dashboard_blog_toggle_publish, name='dashboard_blog_toggle_publish'),
    path('blogs/<int:page_id>/delete/', dashboard_blog_delete, name='dashboard_blog_delete'),
    path("company/", views.company_detail, name="api-company-detail"),
    path("blogs/", views.blog_list, name="api-blog-list"),
    path("blogs/<slug:slug>/", views.blog_detail, name="api-blog-detail"),
    path("categories/", views.category_list, name="api-category-list"),
    path("tags/", views.tag_list, name="api-tag-list"),
]