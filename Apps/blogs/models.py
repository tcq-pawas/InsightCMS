from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel
from wagtail.search import index
from .forms import BlogPageForm

from Apps.accounts.models import User


class BlogIndexPage(Page):
    """Index page for a company's blog posts."""

    parent_page_types = ['companies.CompanyHomePage', 'wagtailcore.Page']
    subpage_types = ['blogs.BlogPage']

    class Meta:
        verbose_name = _('Blog Index')
        verbose_name_plural = _('Blog Indices')

    def get_company(self):
        """Derive company from parent CompanyHomePage."""
        parent = self.get_parent()
        if parent and hasattr(parent, 'specific'):
            parent_specific = parent.specific
            if hasattr(parent_specific, 'company') and parent_specific.company:
                return parent_specific.company
        return None

    def get_context(self, request):
        context = super().get_context(request)
        company = self.get_company()
        posts = BlogPage.objects.child_of(self).live().public().order_by('-first_published_at')
        if company:
            posts = posts.filter(company=company)
        context['blogs'] = posts
        return context


class BlogPage(Page):
    """Blog post page using Wagtail."""

    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='blogs',
        verbose_name=_('Company'),
        help_text=_('Derived automatically from the parent page.')
    )
    featured_image = models.ForeignKey(
        'wagtailimages.Image',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('Featured Image')
    )
    short_description = models.CharField(
        max_length=300,
        verbose_name=_('Short Description')
    )
    body = RichTextField(verbose_name=_('Content'))
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blog_posts',
        verbose_name=_('Author')
    )
    category = models.ForeignKey(
        'BlogCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blogs',
        verbose_name=_('Category')
    )
    tags = models.ManyToManyField(
        'BlogTag',
        blank=True,
        related_name='blogs',
        verbose_name=_('Tags')
    )
    featured = models.BooleanField(
        default=False,
        verbose_name=_('Featured Blog')
    )
    publish_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Publish Date')
    )

    search_fields = Page.search_fields + [
        index.SearchField('title'),
        index.SearchField('short_description'),
        index.SearchField('body'),
        index.FilterField('company'),
        index.FilterField('category'),
        index.FilterField('featured'),
    ]

    # Note: 'company' and 'status' are EXCLUDED from content_panels per rules:
    # 1. Company is derived automatically from parent.
    # 2. Wagtail's live/revision state is the sole publication source of truth.
    content_panels = Page.content_panels + [
        FieldPanel('featured_image'),
        FieldPanel('short_description'),
        FieldPanel('body'),
        FieldPanel('author'),
        FieldPanel('category'),
        FieldPanel('tags'),
        FieldPanel('featured'),
        FieldPanel('publish_date'),
    ]
    
    base_form_class = BlogPageForm

    parent_page_types = ['blogs.BlogIndexPage']
    subpage_types = []

    class Meta:
        verbose_name = _('Blog')
        verbose_name_plural = _('Blogs')

    def __str__(self):
        return self.title

    @property
    def intro(self):
        """Alias property for short_description."""
        return self.short_description

    def save(self, *args, **kwargs):
        """Auto-derive company from parent page if not set."""
        if not self.company_id and self.get_parent():
            parent = self.get_parent().specific
            if hasattr(parent, 'company') and parent.company:
                self.company = parent.company
            elif hasattr(parent, 'get_company'):
                self.company = parent.get_company()
        super().save(*args, **kwargs)


class BlogCategory(models.Model):
    """Blog category model scoped to a company."""
    
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='categories',
        verbose_name=_('Company')
    )
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    slug = models.SlugField(max_length=100, verbose_name=_('Slug'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Blog Category')
        verbose_name_plural = _('Blog Categories')
        ordering = ['name']
        unique_together = ('company', 'slug')

    def __str__(self):
        return f"{self.name} ({self.company.company_name if self.company else 'Global'})"


class BlogTag(models.Model):
    """Blog tag model scoped to a company."""
    
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tags',
        verbose_name=_('Company')
    )
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    slug = models.SlugField(max_length=100, verbose_name=_('Slug'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Blog Tag')
        verbose_name_plural = _('Blog Tags')
        ordering = ['name']
        unique_together = ('company', 'slug')

    def __str__(self):
        return f"{self.name} ({self.company.company_name if self.company else 'Global'})"
