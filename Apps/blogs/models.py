from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel
from wagtail.search import index

from Apps.accounts.models import User


class BlogIndexPage(Page):
    """Index page for blog posts."""
    
    class Meta:
        verbose_name = _('Blog Index')
        verbose_name_plural = _('Blog Indices')

    parent_page_types = ['wagtailcore.Page']
    subpage_types = ['blogs.BlogPage']

    def get_context(self, request):
        context = super().get_context(request)
        context['blogs'] = BlogPage.objects.live().public()
        return context


class BlogPage(Page):
    """Blog post page using Wagtail."""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        PUBLISHED = 'published', _('Published')

    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        related_name='blogs',
        verbose_name=_('Company')
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
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_('Status')
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
        index.FilterField('status'),
        index.FilterField('featured'),
    ]

    content_panels = Page.content_panels + [
        FieldPanel('company'),
        FieldPanel('featured_image'),
        FieldPanel('short_description'),
        FieldPanel('body'),
        FieldPanel('author'),
        FieldPanel('category'),
        FieldPanel('tags'),
        FieldPanel('featured'),
        FieldPanel('status'),
        FieldPanel('publish_date'),
    ]

    parent_page_types = ['blogs.BlogIndexPage']
    subpage_types = []

    class Meta:
        verbose_name = _('Blog')
        verbose_name_plural = _('Blogs')
        ordering = ['-publish_date']

    def __str__(self):
        return self.title


class BlogCategory(models.Model):
    """Blog category model."""
    
    name = models.CharField(max_length=100, unique=True, verbose_name=_('Name'))
    slug = models.SlugField(max_length=100, unique=True, verbose_name=_('Slug'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Blog Category')
        verbose_name_plural = _('Blog Categories')
        ordering = ['name']

    def __str__(self):
        return self.name


class BlogTag(models.Model):
    """Blog tag model."""
    
    name = models.CharField(max_length=100, unique=True, verbose_name=_('Name'))
    slug = models.SlugField(max_length=100, unique=True, verbose_name=_('Slug'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Blog Tag')
        verbose_name_plural = _('Blog Tags')
        ordering = ['name']

    def __str__(self):
        return self.name
