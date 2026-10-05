from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q

from Apps.blogs.models import BlogPage, BlogCategory, BlogTag
from Apps.blogs.serializers import (
    BlogPageSerializer,
    BlogPageListSerializer,
    BlogCategorySerializer,
    BlogTagSerializer,
    BlogCommentSerializer,
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


@api_view(["GET", "POST"])
@authentication_classes([CompanyAPIKeyAuthentication])
@permission_classes([HasValidCompanyAPIKey])
def api_blog_comments(request, slug):
    """API endpoint for external websites to fetch approved comments or submit new comment."""
    company = request.user
    try:
        blog = BlogPage.objects.live().public().get(company=company, slug=slug)
    except BlogPage.DoesNotExist:
        return Response({"detail": "Blog not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        comments = blog.comments.filter(status="approved", parent=None).order_by("-created_at")
        serializer = BlogCommentSerializer(comments, many=True)
        return Response(serializer.data)

    elif request.method == "POST":
        name = request.data.get("author_name", "").strip()
        email = request.data.get("author_email", "").strip()
        content = request.data.get("content", "").strip()

        if not name or not content:
            return Response({"detail": "author_name and content are required."}, status=status.HTTP_400_BAD_REQUEST)

        comment = BlogComment.objects.create(
            blog=blog,
            author_name=name,
            author_email=email,
            content=content,
            status="approved",
        )
        return Response({
            "message": "Comment posted successfully.",
            "id": comment.id,
            "status": comment.status,
        }, status=status.HTTP_201_CREATED)



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



def _get_request_company(user):
    """Helper to safely get company linked to user."""
    profile = getattr(user, 'userprofile', None)
    if profile and profile.company:
        return profile.company
    membership = user.company_memberships.first()
    if membership and membership.company:
        return membership.company
    if user.is_superuser:
        from Apps.companies.models import Company
        return Company.objects.first()
    return None


@login_required(login_url='/login/')
def dashboard_blog_create(request):
    """Create a new BlogPage scoped to logged-in user's Company."""
    company = _get_request_company(request.user)

    if request.method == 'POST':
        title = request.POST.get('title')
        short_description = request.POST.get('short_description', '')
        body = request.POST.get('body', '')
        category_id = request.POST.get('category')
        action_type = request.POST.get('action_type', 'publish')  # 'publish' or 'draft'
        featured_image_file = request.FILES.get('featured_image')

        # Company-specific BlogIndexPage first, else fallback to first index
        blog_index = None
        if company:
            home = company.home_pages.first()
            if home:
                blog_index = BlogIndexPage.objects.filter(path__startswith=home.path).first()
        if not blog_index:
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

        if not short_description:
            import re
            clean_body = re.sub(r'<[^>]+>', ' ', body).strip()
            short_description = (clean_body[:180] + '...') if clean_body else title

        category = None
        if category_id:
            cat_qs = BlogCategory.objects.all()
            if company:
                cat_qs = cat_qs.filter(company=company)
            category = cat_qs.filter(id=category_id).first()

        # Create BlogPage instance strictly scoped to company
        allow_comments = request.POST.get('allow_comments') == 'on' if 'allow_comments' in request.POST else True
        blog_page = BlogPage(
            title=title,
            short_description=short_description,
            body=body,
            category=category,
            featured_image=wagtail_image,
            author=request.user,
            company=company,
            allow_comments=allow_comments,
        )

        # Add to Wagtail page tree
        blog_index.add_child(instance=blog_page)

        # Publish or Save Draft
        # Employee (COMPANY_USER) ke blogs auto-publish nahi honge — approval chahiye
        from Apps.accounts.models import User as UserModel
        if request.user.role == UserModel.Role.COMPANY_USER:
            blog_page.approval_status = BlogPage.APPROVAL_PENDING
            blog_page.save()
            blog_page.unpublish()
            messages.success(request, f"Blog '{title}' submitted for approval. Company Admin will review it.")
        elif action_type == 'publish':
            blog_page.approval_status = BlogPage.APPROVAL_APPROVED
            blog_page.save()
            revision = blog_page.save_revision()
            revision.publish()
            messages.success(request, f"Blog '{title}' published successfully!")
        else:
            blog_page.approval_status = BlogPage.APPROVAL_APPROVED
            blog_page.save()
            blog_page.unpublish()
            messages.success(request, f"Blog '{title}' saved as draft!")

        return redirect('/blog-posts/')

    categories = BlogCategory.objects.all()
    if company:
        categories = categories.filter(company=company)

    from Apps.companies.models import CompanyBlogPostsPage
    from Apps.accounts.models import UserDashboardPage
    blog_posts_page = CompanyBlogPostsPage.objects.live().first()
    dashboard_page = UserDashboardPage.objects.live().first()
    sidebar_links = dashboard_page.sidebar_links if dashboard_page else []

    return render(request, 'blogs/blog_create.html', {
        'categories': categories,
        'page': blog_posts_page,
        'dashboard_page': dashboard_page,
        'sidebar_links': sidebar_links,
        'active_tab': 'posts',
        'user': request.user,
        'company': company,
    })


@login_required(login_url='/login/')
def dashboard_blog_edit(request, page_id):
    """Edit an existing BlogPage - strictly isolated to logged-in user's company."""
    company = _get_request_company(request.user)
    
    # Restrict lookup to own company (superusers bypass)
    from Apps.accounts.models import User as UserModel
    if request.user.is_superuser:
        blog_page = get_object_or_404(BlogPage, id=page_id)
    elif request.user.role == UserModel.Role.COMPANY_USER:
        # Normal user can ONLY edit their own blogs
        blog_page = get_object_or_404(BlogPage, id=page_id, company=company, author=request.user)
    else:
        blog_page = get_object_or_404(BlogPage, id=page_id, company=company)

    if request.method == 'POST':
        blog_page.title = request.POST.get('title', blog_page.title)
        blog_page.short_description = request.POST.get('short_description', blog_page.short_description)
        blog_page.body = request.POST.get('body', blog_page.body)
        blog_page.allow_comments = request.POST.get('allow_comments') == 'on' if 'allow_comments' in request.POST else False
        
        category_id = request.POST.get('category')
        if category_id:
            cat_qs = BlogCategory.objects.all()
            if company:
                cat_qs = cat_qs.filter(company=company)
            blog_page.category = cat_qs.filter(id=category_id).first()

        featured_image_file = request.FILES.get('featured_image')
        if featured_image_file:
            wagtail_image = Image.objects.create(
                title=featured_image_file.name,
                file=featured_image_file
            )
            blog_page.featured_image = wagtail_image

        action_type = request.POST.get('action_type', 'publish')
        revision = blog_page.save_revision()

        # Employee (COMPANY_USER) ke blogs approval ke bina publish nahi honge
        from Apps.accounts.models import User as UserModel
        if request.user.role == UserModel.Role.COMPANY_USER:
            blog_page.approval_status = BlogPage.APPROVAL_PENDING
            blog_page.save()
            blog_page.unpublish()
            messages.success(request, f"Blog '{blog_page.title}' updated & submitted for approval. Company Admin will review it.")
        elif action_type == 'publish':
            blog_page.approval_status = BlogPage.APPROVAL_APPROVED
            blog_page.save()
            revision.publish()
            messages.success(request, f"Blog '{blog_page.title}' updated & published!")
        else:
            blog_page.approval_status = BlogPage.APPROVAL_APPROVED
            blog_page.save()
            blog_page.unpublish()
            messages.success(request, f"Blog '{blog_page.title}' updated as draft!")

        return redirect('/blog-posts/')

    categories = BlogCategory.objects.all()
    if company:
        categories = categories.filter(company=company)

    from Apps.companies.models import CompanyBlogPostsPage
    from Apps.accounts.models import UserDashboardPage
    blog_posts_page = CompanyBlogPostsPage.objects.live().first()
    dashboard_page = UserDashboardPage.objects.live().first()
    sidebar_links = dashboard_page.sidebar_links if dashboard_page else []

    return render(request, 'blogs/blog_edit.html', {
        'blog': blog_page,
        'categories': categories,
        'page': blog_posts_page,
        'dashboard_page': dashboard_page,
        'sidebar_links': sidebar_links,
        'active_tab': 'posts',
        'user': request.user,
        'company': company,
    })


@login_required(login_url='/login/')
def dashboard_blog_toggle_publish(request, page_id):
    """Toggle Publish/Unpublish status - restricted to Company Admins."""
    if request.method == 'POST':
        from Apps.accounts.models import User as UserModel
        if request.user.role == UserModel.Role.COMPANY_USER and not request.user.is_superuser:
            messages.error(request, "Permission denied. Only Company Admins can toggle publish status.")
            return redirect('/blog-posts/')

        company = _get_request_company(request.user)
        if request.user.is_superuser:
            blog_page = get_object_or_404(BlogPage, id=page_id)
        else:
            blog_page = get_object_or_404(BlogPage, id=page_id, company=company)

        if blog_page.live:
            blog_page.unpublish()
            messages.success(request, f"'{blog_page.title}' is now Unpublished (Draft).")
        else:
            blog_page.approval_status = BlogPage.APPROVAL_APPROVED
            blog_page.save()
            revision = blog_page.save_revision()
            revision.publish()
            messages.success(request, f"'{blog_page.title}' is now Published!")

    return redirect('/blog-posts/')


@login_required(login_url='/login/')
def dashboard_blog_delete(request, page_id):
    """Delete a BlogPage - strictly restricted to own company."""
    if request.method == 'POST':
        company = _get_request_company(request.user)
        from Apps.accounts.models import User as UserModel
        if request.user.is_superuser:
            blog_page = get_object_or_404(BlogPage, id=page_id)
        elif request.user.role == UserModel.Role.COMPANY_USER:
            # Normal user can ONLY delete their own blogs
            blog_page = get_object_or_404(BlogPage, id=page_id, company=company, author=request.user)
        else:
            blog_page = get_object_or_404(BlogPage, id=page_id, company=company)

        title = blog_page.title
        blog_page.delete()
        messages.success(request, f"Blog '{title}' deleted successfully!")

    return redirect('/blog-posts/')


@login_required(login_url='/login/')
def dashboard_blog_approve(request, page_id):
    """Company Admin approves (publishes) a pending employee blog draft."""
    from Apps.accounts.models import User as UserModel, UserNotification
    if request.method == 'POST':
        # Only Company Admin or Super Admin can approve
        if request.user.role not in [UserModel.Role.COMPANY_ADMIN] and not request.user.is_superuser:
            messages.error(request, "You don't have permission to approve blogs.")
            return redirect('/blog-posts/')

        company = _get_request_company(request.user)
        if request.user.is_superuser:
            blog_page = get_object_or_404(BlogPage, id=page_id)
        else:
            blog_page = get_object_or_404(BlogPage, id=page_id, company=company)

        blog_page.approval_status = BlogPage.APPROVAL_APPROVED
        blog_page.save()
        revision = blog_page.save_revision()
        revision.publish()

        # Send Notification to Author
        if blog_page.author:
            UserNotification.objects.create(
                user=blog_page.author,
                title="Blog Approved & Published 🎉",
                message=f"Your blog '{blog_page.title}' has been approved and published by Company Admin.",
                notification_type='approved'
            )

        messages.success(request, f"✅ Blog '{blog_page.title}' approved & published successfully!")

    return redirect('/blog-posts/')


@login_required(login_url='/login/')
def dashboard_blog_reject(request, page_id):
    """Company Admin rejects a pending employee blog submission."""
    from Apps.accounts.models import User as UserModel, UserNotification
    if request.method == 'POST':
        if request.user.role not in [UserModel.Role.COMPANY_ADMIN] and not request.user.is_superuser:
            messages.error(request, "You don't have permission to reject blogs.")
            return redirect('/blog-posts/')

        company = _get_request_company(request.user)
        if request.user.is_superuser:
            blog_page = get_object_or_404(BlogPage, id=page_id)
        else:
            blog_page = get_object_or_404(BlogPage, id=page_id, company=company)

        blog_page.approval_status = BlogPage.APPROVAL_REJECTED
        blog_page.save()
        blog_page.unpublish()

        # Send Notification to Author
        if blog_page.author:
            UserNotification.objects.create(
                user=blog_page.author,
                title="Blog Status Update ❌",
                message=f"Your blog '{blog_page.title}' was reviewed and rejected by Company Admin.",
                notification_type='rejected'
            )

        messages.warning(request, f"❌ Blog '{blog_page.title}' has been rejected.")

    return redirect('/blog-posts/')

@login_required(login_url='/login/')
def dashboard_website_integration(request):
    """View to provide ready-made RSS feed integration docs & snippets for logged-in company."""
    from Apps.accounts.models import User as UserModel
    if request.user.role == UserModel.Role.COMPANY_USER:
        messages.error(request, "Access restricted. Integration settings are for Company Admins only.")
        return redirect('/dashboard/')

    company = _get_request_company(request.user)
    
    company_slug = company.slug if (company and company.slug) else "your-company"
    company_name = company.company_name if company else "Your Company"

    # Priority: company.website_url > settings.CMS_SITE_URL > request domain
    # Company admin can set their website URL from the Settings page.
    from django.conf import settings as django_settings

    company_website_url = (company.website_url or "").rstrip("/") if company else ""
    fallback_url = getattr(django_settings, 'CMS_SITE_URL', None) or request.build_absolute_uri('/')[:-1]
    cms_base_url = company_website_url if company_website_url else fallback_url


    
    from Apps.accounts.models import UserDashboardPage
    dashboard_page = UserDashboardPage.objects.live().first()
    sidebar_links = dashboard_page.sidebar_links if dashboard_page else []

    return render(request, 'blogs/website_integration.html', {
        'company': company,
        'company_slug': company_slug,
        'company_name': company_name,
        'cms_base_url': cms_base_url,
        'dashboard_page': dashboard_page,
        'sidebar_links': sidebar_links,
        'active_tab': 'integration',
        'user': request.user,
    })


# ──────────────────────────────────────────────────────────────────────────────
# COMMENT SYSTEM VIEWS
# ──────────────────────────────────────────────────────────────────────────────

from Apps.blogs.models import BlogComment
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings as django_settings_mail


def comment_submit(request, page_id):
    """Public view — visitors submit a comment on a blog post page."""
    blog = get_object_or_404(BlogPage, pk=page_id)
    if request.method == 'POST':
        name = request.POST.get('author_name', '').strip()
        email = request.POST.get('author_email', '').strip()
        content = request.POST.get('content', '').strip()

        if not getattr(blog, 'allow_comments', True):
            messages.error(request, 'Comments are closed for this blog post.')
            return redirect(blog.full_url if hasattr(blog, 'full_url') else '/')

        if name and content:
            comment = BlogComment.objects.create(
                blog=blog,
                author_name=name,
                author_email=email,
                content=content,
                status='pending',
            )
            # Email notification to blog author + admin
            recipients = []
            if blog.owner and blog.owner.email:
                recipients.append(blog.owner.email)
            # Also notify company admin if different
            if blog.company:
                from Apps.companies.models import UserProfile
                admins = UserProfile.objects.filter(
                    company=blog.company,
                    user__role='company_admin',
                    user__is_active=True
                ).values_list('user__email', flat=True)
                recipients += list(admins)
                if not recipients and blog.company.email:
                    recipients.append(blog.company.email)
            recipients = list(set(r for r in recipients if r))
            if recipients:
                try:
                    send_mail(
                        subject=f'New comment on "{blog.title}"',
                        message=(
                            f'A new comment was posted by {name} ({email}):\n\n'
                            f'"{content}"\n\n'
                            f'Visit your dashboard to view or moderate it:\n'
                            f'http://127.0.0.1:8000/comments/?status=pending\n'
                        ),
                        from_email=getattr(django_settings_mail, 'DEFAULT_FROM_EMAIL', 'noreply@insightcms.com'),
                        recipient_list=recipients,
                        fail_silently=True,
                    )
                except Exception:
                    pass
            messages.success(request, 'Your comment has been submitted and is awaiting approval.')
        else:
            messages.error(request, 'Name and comment are required.')

    return redirect(blog.full_url if hasattr(blog, 'full_url') else '/')


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@csrf_exempt
def comment_submit_by_slug(request, slug):
    """
    Public endpoint for external sites (e.g. HeyDay/Hectare) to:
    1. GET /blogs/<slug>/comments/submit/ -> returns JSON array of approved comments + replies
    2. POST /blogs/<slug>/comments/submit/ -> submits a comment and returns JSON result
    """
    blog = BlogPage.objects.live().filter(slug=slug).first()
    if not blog:
        return JsonResponse({'error': 'Blog post not found.'}, status=404)

    def serialize_comment(c):
        child_replies = []
        for r in c.replies.filter(status='approved').order_by('created_at'):
            child_replies.append(serialize_comment(r))
        return {
            'id': c.id,
            'author_name': c.author_name,
            'author_email': c.author_email,
            'content': c.content,
            'created_at': c.created_at.strftime('%b %d, %Y'),
            'is_team': bool(c.admin_user),
            'replies': child_replies,
        }

    if request.method == 'GET':
        if not getattr(blog, 'allow_comments', True):
            return JsonResponse({'success': True, 'allow_comments': False, 'count': 0, 'comments': []})
        root_comments = blog.comments.filter(status='approved', parent=None).order_by('-created_at')
        comments_data = [serialize_comment(c) for c in root_comments]
        return JsonResponse({'success': True, 'allow_comments': True, 'count': len(comments_data), 'comments': comments_data})

    elif request.method == 'POST':
        # Accept JSON body or regular form data
        name = ''
        email = ''
        content = ''
        parent_id = None
        action = None
        comment_id = None

        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body.decode('utf-8'))
                action = data.get('action')
                comment_id = data.get('comment_id')
                name = data.get('author_name', '').strip()
                email = data.get('author_email', '').strip()
                content = data.get('content', '').strip()
                parent_id = data.get('parent_id')
            except Exception:
                pass
        else:
            action = request.POST.get('action')
            comment_id = request.POST.get('comment_id')
            name = request.POST.get('author_name', '').strip()
            email = request.POST.get('author_email', '').strip()
            content = request.POST.get('content', '').strip()
            parent_id = request.POST.get('parent_id')

        # Handle comment deletion
        if action == 'delete' and comment_id:
            del_comment = BlogComment.objects.filter(pk=comment_id, blog=blog).first()
            if del_comment:
                del_comment.delete()
                return JsonResponse({'success': True, 'message': 'Comment deleted successfully.'})
            return JsonResponse({'error': 'Comment not found.'}, status=404)

        if not getattr(blog, 'allow_comments', True):
            return JsonResponse({'error': 'Comments are disabled for this blog post.'}, status=403)

        if not name or not content:
            return JsonResponse({'error': 'Author name and comment content are required.'}, status=400)

        parent_comment = None
        if parent_id:
            parent_comment = BlogComment.objects.filter(pk=parent_id, blog=blog).first()

        comment = BlogComment.objects.create(
            blog=blog,
            author_name=name,
            author_email=email,
            content=content,
            parent=parent_comment,
            status='pending',
        )

        # Send email notifications
        recipients = []
        if blog.owner and blog.owner.email:
            recipients.append(blog.owner.email)
        if blog.company:
            from Apps.companies.models import UserProfile
            admins = UserProfile.objects.filter(
                company=blog.company,
                user__role='company_admin',
                user__is_active=True
            ).values_list('user__email', flat=True)
            recipients += list(admins)
            if not recipients and blog.company.email:
                recipients.append(blog.company.email)
        recipients = list(set(r for r in recipients if r))
        if recipients:
            try:
                send_mail(
                    subject=f'New comment on "{blog.title}"',
                    message=(
                        f'A new comment was posted by {name} ({email}):\n\n'
                        f'"{content}"\n\n'
                        f'Visit your dashboard to view or moderate it:\n'
                        f'http://127.0.0.1:8000/comments/?status=pending\n'
                    ),
                    from_email=getattr(django_settings_mail, 'DEFAULT_FROM_EMAIL', 'noreply@insightcms.com'),
                    recipient_list=recipients,
                    fail_silently=True,
                )
            except Exception:
                pass

        return JsonResponse({
            'success': True,
            'message': 'Your comment has been submitted and is awaiting admin approval.',
            'comment_id': comment.id,
            'status': 'pending'
        }, status=201)

    return JsonResponse({'error': 'Method not allowed.'}, status=405)


@login_required(login_url='/login/')
def dashboard_comments_view(request):
    """Dashboard — list all comments for this company's blogs with blog filter and counts."""
    from Apps.accounts.models import User as UserModel, UserDashboardPage
    from Apps.blogs.models import BlogPage
    user = request.user
    company = _get_request_company(user)

    if user.role == UserModel.Role.COMPANY_USER:
        blogs_list = BlogPage.objects.live().filter(owner=user).order_by('title')
        base_comments = BlogComment.objects.filter(blog__owner=user)
    else:
        blogs_list = BlogPage.objects.live().filter(company=company).order_by('title')
        base_comments = BlogComment.objects.filter(blog__company=company)

    # Filter by specific Blog Post
    selected_blog_id = request.GET.get('blog_id')
    selected_blog = None
    if selected_blog_id:
        try:
            selected_blog = blogs_list.filter(id=int(selected_blog_id)).first()
            if selected_blog:
                base_comments = base_comments.filter(blog=selected_blog)
        except (ValueError, TypeError):
            selected_blog_id = None

    # Calculate scope counts (Total, Pending, Approved, Rejected)
    total_count = base_comments.count()
    pending_count = base_comments.filter(status='pending').count()
    approved_count = base_comments.filter(status='approved').count()
    rejected_count = base_comments.filter(status__in=['rejected', 'spam']).count()

    comments = base_comments.select_related('blog', 'parent', 'admin_user').order_by('-created_at')

    # Filter by status tab
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'pending':
        comments = comments.filter(status='pending')
    elif status_filter == 'approved':
        comments = comments.filter(status='approved')
    elif status_filter in ('rejected', 'spam'):
        comments = comments.filter(status__in=['rejected', 'spam'])

    dashboard_page = UserDashboardPage.objects.live().first()
    sidebar_links = dashboard_page.sidebar_links if dashboard_page else []

    return render(request, 'blogs/dashboard_comments.html', {
        'comments': comments,
        'blogs_list': blogs_list,
        'selected_blog_id': int(selected_blog_id) if selected_blog_id else None,
        'selected_blog': selected_blog,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'status_filter': status_filter,
        'sidebar_links': sidebar_links,
        'active_tab': 'comments',
        'user': user,
        'company': company,
        'is_employee': user.role == UserModel.Role.COMPANY_USER,
        'dashboard_page': dashboard_page,
    })


@login_required(login_url='/login/')
def comment_approve(request, comment_id):
    """Approve a pending comment OR restore a rejected/spam comment back to approved."""
    from Apps.accounts.models import User as UserModel
    comment = get_object_or_404(BlogComment, pk=comment_id)
    company = _get_request_company(request.user)

    # Permission check
    if request.user.role == UserModel.Role.COMPANY_USER:
        if comment.blog.owner != request.user:
            messages.error(request, 'You do not have permission to approve this comment.')
            return redirect('dashboard_comments')
    else:
        if comment.blog.company != company:
            messages.error(request, 'Access denied.')
            return redirect('dashboard_comments')

    was_rejected = comment.status in ('rejected', 'spam')
    comment.status = 'approved'
    comment.save(update_fields=['status'])
    if was_rejected:
        messages.success(request, 'Comment restored to Approved.')
    else:
        messages.success(request, 'Comment approved.')
    return redirect('dashboard_comments')


@login_required(login_url='/login/')
def comment_delete(request, comment_id):
    """Delete (or mark rejected/spam) a comment."""
    from Apps.accounts.models import User as UserModel
    comment = get_object_or_404(BlogComment, pk=comment_id)
    company = _get_request_company(request.user)

    if request.user.role == UserModel.Role.COMPANY_USER:
        if comment.blog.owner != request.user:
            messages.error(request, 'You do not have permission.')
            return redirect('dashboard_comments')
    else:
        if comment.blog.company != company:
            messages.error(request, 'Access denied.')
            return redirect('dashboard_comments')

    action = request.POST.get('action', 'delete')
    if action in ('reject', 'rejected', 'spam'):
        comment.status = 'rejected'
        comment.save(update_fields=['status'])
        messages.success(request, 'Comment marked as rejected.')
    else:
        comment.delete()
        messages.success(request, 'Comment deleted.')
    return redirect('dashboard_comments')


@login_required(login_url='/login/')
def comment_reply(request, comment_id):
    """Admin/Author replies to a visitor comment from the dashboard."""
    from Apps.accounts.models import User as UserModel
    parent_comment = get_object_or_404(BlogComment, pk=comment_id)
    company = _get_request_company(request.user)

    if request.user.role == UserModel.Role.COMPANY_USER:
        if parent_comment.blog.owner != request.user:
            messages.error(request, 'You do not have permission.')
            return redirect('dashboard_comments')
    else:
        if parent_comment.blog.company != company:
            messages.error(request, 'Access denied.')
            return redirect('dashboard_comments')

    if request.method == 'POST':
        reply_content = request.POST.get('reply_content', '').strip()
        if reply_content:
            reply = BlogComment.objects.create(
                blog=parent_comment.blog,
                author_name=request.user.get_full_name() or request.user.email,
                author_email=request.user.email,
                content=reply_content,
                status='approved',   # admin replies are auto-approved
                parent=parent_comment,
                admin_user=request.user,
            )
            # Notify the original commenter by email
            if parent_comment.author_email:
                try:
                    send_mail(
                        subject=f'Reply to your comment on "{parent_comment.blog.title}"',
                        message=(
                            f'Hi {parent_comment.author_name},\n\n'
                            f'The team replied to your comment:\n\n'
                            f'Your comment: "{parent_comment.content}"\n\n'
                            f'Reply: "{reply_content}"\n\n'
                            f'Visit the blog post to see the full conversation.'
                        ),
                        from_email=getattr(django_settings_mail, 'DEFAULT_FROM_EMAIL', 'noreply@insightcms.com'),
                        recipient_list=[parent_comment.author_email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
            messages.success(request, 'Reply posted successfully.')
        else:
            messages.error(request, 'Reply cannot be empty.')

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'dashboard_comments'
    return redirect(next_url)


@login_required(login_url='/login/')
def comments_bulk_action(request):
    """Bulk delete, bulk approve, or bulk spam selected comments."""
    from Apps.accounts.models import User as UserModel
    if request.method == 'POST':
        action = request.POST.get('bulk_action', 'delete')
        comment_ids = request.POST.getlist('selected_comments')

        if not comment_ids:
            messages.warning(request, 'Please select at least one comment.')
            return redirect('dashboard_comments')

        company = _get_request_company(request.user)
        if request.user.role == UserModel.Role.COMPANY_USER:
            qs = BlogComment.objects.filter(id__in=comment_ids, blog__owner=request.user)
        else:
            qs = BlogComment.objects.filter(id__in=comment_ids, blog__company=company)

        count = qs.count()
        if action == 'delete':
            qs.delete()
            messages.success(request, f'Successfully deleted {count} comment(s).')
        elif action == 'spam':
            qs.update(status='spam')
            messages.success(request, f'Successfully marked {count} comment(s) as spam.')
        elif action == 'approve':
            qs.update(status='approved')
            messages.success(request, f'Successfully approved {count} comment(s).')

    return redirect('dashboard_comments')