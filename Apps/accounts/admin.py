from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from Apps.accounts.models import User


class UserAdmin(BaseUserAdmin):
    """Custom admin for User model."""
    
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active']
    list_filter = ['role', 'is_staff', 'is_active', 'is_approved']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-created_at']
    actions = ['approve_users', 'reject_users']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'avatar')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_approved', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )
    
    def approve_users(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} user(s) approved successfully.")
    approve_users.short_description = "✅ Approve selected users"

    def reject_users(self, request, queryset):
        updated = queryset.update(is_approved=False, is_active=False)
        self.message_user(request, f"{updated} user(s) rejected/deactivated.")
    reject_users.short_description = "❌ Reject selected users"

admin.site.register(User, UserAdmin)
