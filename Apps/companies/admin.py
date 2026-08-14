from django.contrib import admin
from Apps.companies.models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Admin interface for Company model."""
    
    list_display = ['company_name', 'slug', 'domain', 'website_name', 'email', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['company_name', 'slug', 'domain', 'website_name', 'email', 'contact_person']
    readonly_fields = ['api_key', 'created_at', 'updated_at']
    prepopulated_fields = {'slug': ('company_name',)}
    
    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'slug', 'domain', 'website_name', 'website_url', 'logo')
        }),
        ('Contact Information', {
            'fields': ('email', 'contact_person')
        }),
        ('Status & API', {
            'fields': ('status', 'api_key')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['regenerate_api_keys']

    def regenerate_api_keys(self, request, queryset):
        """Admin action to regenerate API keys for selected companies."""
        count = 0
        for company in queryset:
            company.regenerate_api_key()
            count += 1
        self.message_user(request, f'Successfully regenerated API keys for {count} companies.')
    
    regenerate_api_keys.short_description = 'Regenerate API keys for selected companies'


from Apps.companies.models import CompanyMembership

@admin.register(CompanyMembership)
class CompanyMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'role', 'created_at']
    list_filter = ['role', 'company', 'created_at']
    search_fields = ['user__email', 'company__company_name']

