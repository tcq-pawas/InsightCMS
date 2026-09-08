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


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseNotAllowed
from Apps.blogs.models import BlogPage, BlogIndexPage, BlogCategory
from wagtail.images.models import Image

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



@login_required(login_url='/login/')
def dashboard_blog_create(request):
    """Create a new BlogPage from custom Dashboard."""
    if request.method == 'POST':
        title = request.POST.get('title')
        short_description = request.POST.get('short_description', '')
        body = request.POST.get('body', '')
        category_id = request.POST.get('category')
        action_type = request.POST.get('action_type', 'publish')  # 'publish' or 'draft'
        featured_image_file = request.FILES.get('featured_image')

        blog_index = BlogIndexPage.objects.first()
        if not blog_index:
            messages.error(request, "Blog Index Page not found in Wagtail!")
            return redirect('/blog-posts/')

        # Handle Image Upload if provided
        wagtail_image = None
        if featured_image_file:
            wagtail_image = Image.objects.create(
                title=featured_image_file.name,
                file=featured_image_file
            )

        category = BlogCategory.objects.filter(id=category_id).first() if category_id else None

        # Create BlogPage instance
        blog_page = BlogPage(
            title=title,
            short_description=short_description,
            body=body,
            category=category,
            featured_image=wagtail_image,
            author=request.user
        )

        # Add to Wagtail page tree
        blog_index.add_child(instance=blog_page)

        # Publish or Save Draft
        revision = blog_page.save_revision()
        if action_type == 'publish':
            revision.publish()
            messages.success(request, f"Blog '{title}' published successfully!")
        else:
            messages.success(request, f"Blog '{title}' saved as draft!")

        return redirect('/blog-posts/')

    categories = BlogCategory.objects.all()
    return render(request, 'blogs/blog_create.html', {'categories': categories})


@login_required(login_url='/login/')
def dashboard_blog_edit(request, page_id):
    """Edit an existing BlogPage from custom Dashboard."""
    blog_page = get_object_or_404(BlogPage, id=page_id)

    if request.method == 'POST':
        blog_page.title = request.POST.get('title', blog_page.title)
        blog_page.short_description = request.POST.get('short_description', blog_page.short_description)
        blog_page.body = request.POST.get('body', blog_page.body)
        
        category_id = request.POST.get('category')
        if category_id:
            blog_page.category = BlogCategory.objects.filter(id=category_id).first()

        featured_image_file = request.FILES.get('featured_image')
        if featured_image_file:
            wagtail_image = Image.objects.create(
                title=featured_image_file.name,
                file=featured_image_file
            )
            blog_page.featured_image = wagtail_image

        action_type = request.POST.get('action_type', 'publish')
        revision = blog_page.save_revision()

        if action_type == 'publish':
            revision.publish()
            messages.success(request, f"Blog '{blog_page.title}' updated & published!")
        else:
            blog_page.unpublish()
            messages.success(request, f"Blog '{blog_page.title}' updated as draft!")

        return redirect('/blog-posts/')

    categories = BlogCategory.objects.all()
    return render(request, 'blogs/blog_edit.html', {
        'blog': blog_page,
        'categories': categories
    })


@login_required(login_url='/login/')
def dashboard_blog_toggle_publish(request, page_id):
    """Toggle Publish/Unpublish status of a BlogPage."""
    if request.method == 'POST':
        blog_page = get_object_or_404(BlogPage, id=page_id)
        if blog_page.live:
            blog_page.unpublish()
            messages.success(request, f"'{blog_page.title}' is now Unpublished (Draft).")
        else:
            revision = blog_page.save_revision()
            revision.publish()
            messages.success(request, f"'{blog_page.title}' is now Published!")

    return redirect('/blog-posts/')


@login_required(login_url='/login/')
def dashboard_blog_delete(request, page_id):
    """Delete a BlogPage from custom Dashboard."""
    if request.method == 'POST':
        blog_page = get_object_or_404(BlogPage, id=page_id)
        title = blog_page.title
        blog_page.delete()
        messages.success(request, f"Blog '{title}' deleted successfully!")

    return redirect('/blog-posts/')