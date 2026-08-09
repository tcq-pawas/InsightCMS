from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Apps.api.views import BlogViewSet, CategoryViewSet, TagViewSet, CompanyViewSet


router = DefaultRouter()
router.register(r'blogs', BlogViewSet, basename='blog')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'company', CompanyViewSet, basename='company')

urlpatterns = [
    path('', include(router.urls)),
]
