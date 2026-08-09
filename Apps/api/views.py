from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django_filters.rest_framework import DjangoFilterBackend
from wagtail.models import Page
from Apps.blogs.models import BlogPage, BlogCategory, BlogTag
from Apps.blogs.serializers import (
    BlogPageSerializer, BlogPageListSerializer, 
    BlogCategorySerializer, BlogTagSerializer
)
from Apps.companies.serializers import CompanySerializer
from Apps.common.permissions import IsCompanyAuthenticated
from Apps.api.pagination import StandardResultsSetPagination


@swagger_auto_schema(
    tags=['Blogs'],
    operation_description="API endpoint for blog posts. Only returns published blogs for the authenticated company.",
    responses={200: BlogPageListSerializer, 404: 'Blog not found'}
)
class BlogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for blog posts.
    Only returns published blogs for the authenticated company.
    """
    permission_classes = [IsCompanyAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'tags', 'featured']
    search_fields = ['title', 'short_description']
    ordering_fields = ['publish_date', 'created_at']
    ordering = ['-publish_date']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """
        Filter blogs to only return published blogs for the authenticated company.
        """
        if getattr(self, 'swagger_fake_view', False):
            return BlogPage.objects.none()
        company = self.request.company
        return BlogPage.objects.live().public().filter(
            company=company,
            status=BlogPage.Status.PUBLISHED
        ).select_related('company', 'author', 'category').prefetch_related('tags')

    def get_serializer_class(self):
        """
        Use lightweight serializer for list view, detailed serializer for detail view.
        """
        if self.action == 'list':
            return BlogPageListSerializer
        return BlogPageSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single blog by slug.
        """
        slug = kwargs.get('pk')
        try:
            blog = self.get_queryset().get(slug=slug)
            serializer = self.get_serializer(blog)
            return Response(serializer.data)
        except BlogPage.DoesNotExist:
            return Response(
                {'detail': 'Blog not found.'},
                status=status.HTTP_404_NOT_FOUND
            )


@swagger_auto_schema(
    tags=['Categories'],
    operation_description="API endpoint for blog categories.",
    responses={200: BlogCategorySerializer}
)
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for blog categories.
    """
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer
    permission_classes = [IsCompanyAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


@swagger_auto_schema(
    tags=['Tags'],
    operation_description="API endpoint for blog tags.",
    responses={200: BlogTagSerializer}
)
class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for blog tags.
    """
    queryset = BlogTag.objects.all()
    serializer_class = BlogTagSerializer
    permission_classes = [IsCompanyAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


@swagger_auto_schema(
    tags=['Company'],
    operation_description="API endpoint for company information. Returns the authenticated company's details.",
    responses={200: CompanySerializer}
)
class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for company information.
    Returns the authenticated company's details.
    """
    permission_classes = [IsCompanyAuthenticated]
    serializer_class = CompanySerializer

    def get_queryset(self):
        """
        Only return the authenticated company.
        """
        if getattr(self, 'swagger_fake_view', False):
            return []
        return [self.request.company]

    def list(self, request, *args, **kwargs):
        """
        Return the authenticated company's details.
        """
        serializer = self.get_serializer(request.company)
        return Response(serializer.data)
