from django.contrib import admin
from Apps.blogs.models import BlogCategory, BlogTag


class BlogCategoryAdmin(admin.ModelAdmin):
    """Admin interface for BlogCategory model."""
    
    list_display = ['name', 'company', 'slug', 'created_at']
    list_filter = ['company', 'created_at']
    search_fields = ['name', 'slug', 'company__company_name']
    prepopulated_fields = {'slug': ('name',)}


class BlogTagAdmin(admin.ModelAdmin):
    """Admin interface for BlogTag model."""
    
    list_display = ['name', 'company', 'slug', 'created_at']
    list_filter = ['company', 'created_at']
    search_fields = ['name', 'slug', 'company__company_name']
    prepopulated_fields = {'slug': ('name',)}


admin.site.register(BlogCategory, BlogCategoryAdmin)
admin.site.register(BlogTag, BlogTagAdmin)
