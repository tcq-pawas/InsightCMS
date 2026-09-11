from django.contrib import admin
from Apps.companies.models import Company, UserProfile


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Admin interface for Company model."""

    list_display = ("company_name", "website_url", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("company_name",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for UserProfile model."""

    list_display = ("user", "company")
    search_fields = ("user__email", "company__company_name")



from Apps.companies.models import CompanyMembership

@admin.register(CompanyMembership)
class CompanyMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'role', 'created_at']
    list_filter = ['role', 'company', 'created_at']
    search_fields = ['user__email', 'company__company_name']

