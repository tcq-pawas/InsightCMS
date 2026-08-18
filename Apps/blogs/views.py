from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q

from Apps.blogs.models import BlogPage, BlogCategory, BlogTag
from Apps.blogs.serializers import (
    BlogPageSerializer,
    BlogPageListSerializer,
    BlogCategorySerializer,
    BlogTagSerializer,
)
from Apps.companies.authentication import CompanyAPIKeyAuthentication
from Apps.companies.api_permissions import HasValidCompanyAPIKey


@api_view(["GET"])
@authentication_classes([CompanyAPIKeyAuthentication])
@permission_classes([HasValidCompanyAPIKey])
def blog_list(request):
    company = request.user
    queryset = BlogPage.objects.live().public().filter(company=company)

    search = request.query_params.get("search")
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) | Q(short_description__icontains=search)
        )

    category_slug = request.query_params.get("category")
    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)

    tag_slug = request.query_params.get("tag")
    if tag_slug:
        queryset = queryset.filter(tags__slug=tag_slug)

    featured = request.query_params.get("featured")
    if featured is not None:
        queryset = queryset.filter(featured=featured.lower() in ("true", "1"))

    ordering = request.query_params.get("ordering", "-publish_date")
    allowed_ordering = {"publish_date", "-publish_date", "title", "-title"}
    if ordering not in allowed_ordering:
        ordering = "-publish_date"
    queryset = queryset.order_by(ordering).distinct()

    paginator = PageNumberPagination()
    paginator.page_size = int(request.query_params.get("page_size", 10))
    page = paginator.paginate_queryset(queryset, request)

    serializer = BlogPageListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
@authentication_classes([CompanyAPIKeyAuthentication])
@permission_classes([HasValidCompanyAPIKey])
def blog_detail(request, slug):
    company = request.user
    try:
        blog = BlogPage.objects.live().public().get(company=company, slug=slug)
    except BlogPage.DoesNotExist:
        return Response({"detail": "Blog not found."}, status=404)

    serializer = BlogPageSerializer(blog)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes([CompanyAPIKeyAuthentication])
@permission_classes([HasValidCompanyAPIKey])
def category_list(request):
    company = request.user
    categories = BlogCategory.objects.filter(company=company)
    serializer = BlogCategorySerializer(categories, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes([CompanyAPIKeyAuthentication])
@permission_classes([HasValidCompanyAPIKey])
def tag_list(request):
    company = request.user
    tags = BlogTag.objects.filter(company=company)
    serializer = BlogTagSerializer(tags, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes([CompanyAPIKeyAuthentication])
@permission_classes([HasValidCompanyAPIKey])
def company_detail(request):
    from Apps.companies.serializers import CompanySerializer
    serializer = CompanySerializer(request.user)
    return Response(serializer.data)