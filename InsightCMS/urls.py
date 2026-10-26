from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from wagtail.contrib.sitemaps.views import sitemap
from Apps.blogs.feeds import CompanyBlogFeed
from Apps.accounts.views import (
    user_dashboard_view,
    logout_view,
    settings_view,
    forgot_password_view,
    set_password_confirm_view,
    user_profile_view,
    blog_comments_settings_view,
    manage_users_settings_view,
    google_oauth_connect_view,
    google_oauth_callback_view,
    google_oauth_disconnect_view,
)
from Apps.blogs.views import (
    dashboard_blog_create,
    dashboard_blog_edit,
    dashboard_comments_view,
    comment_submit,
    comment_approve,
    comment_delete,
    comment_reply,
    comment_submit_by_slug,
    comments_bulk_action,
    dashboard_blog_toggle_publish,
    dashboard_blog_delete,
    dashboard_blog_approve,
    dashboard_blog_reject,
    dashboard_website_integration,
    dashboard_analytics_view,
    dashboard_seo_view,
    dashboard_redirect_add,
    dashboard_redirect_delete,
    robots_txt,
)


# Restrict Django global admin (/admin/) exclusively to platform Super Admins
admin.site.has_permission = lambda request: (
    request.user.is_active and (
        request.user.is_superuser or 
        getattr(request.user, 'role', None) == 'super_admin'
    )
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cms/', include(wagtailadmin_urls)),
    path('company/<slug:company_slug>/rss/', CompanyBlogFeed(), name='company_blog_rss'),
    path('dashboard/', include([
        path('', user_dashboard_view, name='dashboard'),
        path('settings/', settings_view, name='dashboard_settings'),
        path('blogs/create/', dashboard_blog_create, name='dashboard_blog_create'),
        path('blogs/<int:page_id>/edit/', dashboard_blog_edit, name='dashboard_blog_edit'),
        path('blogs/<int:page_id>/toggle-publish/', dashboard_blog_toggle_publish, name='dashboard_blog_toggle_publish'),
        path('blogs/<int:page_id>/delete/', dashboard_blog_delete, name='dashboard_blog_delete'),
        path('blogs/<int:page_id>/approve/', dashboard_blog_approve, name='dashboard_blog_approve'),
        path('blogs/<int:page_id>/reject/', dashboard_blog_reject, name='dashboard_blog_reject'),
        # Analytics & Reports
        path('analytics/', dashboard_analytics_view, name='dashboard_analytics'),
        # SEO & Growth Management
        path('seo/', dashboard_seo_view, name='dashboard_seo'),
        path('seo/redirects/add/', dashboard_redirect_add, name='dashboard_redirect_add'),
        path('seo/redirects/<int:redirect_id>/delete/', dashboard_redirect_delete, name='dashboard_redirect_delete'),
        # Comments inside dashboard
        path('comments/', dashboard_comments_view, name='dashboard_comments_alias'),
        path('comments/<int:comment_id>/approve/', comment_approve, name='comment_approve_alias'),
        path('comments/<int:comment_id>/delete/', comment_delete, name='comment_delete_alias'),
        path('comments/<int:comment_id>/reply/', comment_reply, name='comment_reply_alias'),
    ])),
    # XML Sitemap & Robots.txt
    path('sitemap.xml', sitemap, name='sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    # Direct Analytics & SEO aliases
    path('analytics/', dashboard_analytics_view, name='analytics_alias'),
    path('seo/', dashboard_seo_view, name='seo_alias'),
    # Posts alias redirect
    path('posts/', RedirectView.as_view(url='/blog-posts/', permanent=False), name='posts_alias'),
    # Blog post creation route
    path('blog-posts/create/', dashboard_blog_create, name='legacy_blog_create'),
    # Root level comments URL (http://127.0.0.1:8000/comments/)
    path('comments/', dashboard_comments_view, name='dashboard_comments'),
    path('comments/<int:comment_id>/approve/', comment_approve, name='comment_approve'),
    path('comments/<int:comment_id>/delete/', comment_delete, name='comment_delete'),
    path('comments/<int:comment_id>/reply/', comment_reply, name='comment_reply'),
    path('comments/bulk-action/', comments_bulk_action, name='comments_bulk_action'),
    # Public comment submit (no login required — for blog post page & external sites)
    path('blogs/<int:page_id>/comments/submit/', comment_submit, name='comment_submit'),
    path('blogs/<slug:slug>/comments/submit/', comment_submit_by_slug, name='comment_submit_slug'),
    path('blogs/<slug:slug>/comments/api/', comment_submit_by_slug, name='comment_api_slug'),
    path('settings/', settings_view, name='settings'),
    path('settings/blog/comments/', blog_comments_settings_view, name='blog_comments_settings'),
    path('settings/users/', manage_users_settings_view, name='manage_users_settings'),
    path('dashboard/settings/blog/comments/', blog_comments_settings_view, name='dashboard_blog_comments_settings'),
    path('dashboard/settings/users/', manage_users_settings_view, name='dashboard_manage_users_settings'),
    path('my-profile/', user_profile_view, name='my_profile'),
    path('logout/', logout_view, name='logout'),
    path('password-reset/', forgot_password_view, name='password_reset'),
    path('set-password/<uidb64>/<token>/', set_password_confirm_view, name='set_password_confirm'),
    path('documents/', include(wagtaildocs_urls)),
    path("api/v1/", include("Apps.blogs.urls")),
    path('dashboard/integration/', dashboard_website_integration, name='company_integration_docs'),
    path('integrations/google/connect/', google_oauth_connect_view, name='google_oauth_connect'),
    path('integrations/google/callback/', google_oauth_callback_view, name='google_oauth_callback'),
    path('integrations/google/disconnect/', google_oauth_disconnect_view, name='google_oauth_disconnect'),
    path('', include(wagtail_urls)),  
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)