from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from Apps.accounts.views import user_dashboard_view, logout_view, settings_view


urlpatterns = [
    path('admin/', admin.site.urls),
    path('cms/', include(wagtailadmin_urls)),
    path('dashboard/', user_dashboard_view, name='dashboard'),
    path('settings/', settings_view, name='settings'),
    path('dashboard/settings/', settings_view, name='dashboard_settings'),
    path('logout/', logout_view, name='logout'),
    path('documents/', include(wagtaildocs_urls)),
    path("api/v1/", include("Apps.blogs.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # path('manager/', include('Apps.manager.urls')),
    path('', include(wagtail_urls)),  
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)