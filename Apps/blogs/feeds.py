from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from django.utils.html import strip_tags
from Apps.companies.models import Company
from Apps.blogs.models import BlogPage


class CompanyBlogFeed(Feed):
    """RSS Feed for a specific company's published blogs."""

    def __call__(self, request, *args, **kwargs):
        response = super().__call__(request, *args, **kwargs)
        response["Access-Control-Allow-Origin"] = "*"
        return response

    def get_object(self, request, company_slug):
        """Fetch active company by its slug or raise 404."""
        return get_object_or_404(Company, slug=company_slug)

    def title(self, obj):
        return f"{obj.company_name} - Published Blogs"

    def link(self, obj):
        if hasattr(obj, 'website_url') and obj.website_url:
            return obj.website_url
        return f"/company/{obj.slug}/"

    def feed_url(self, obj):
        return f"/company/{obj.slug}/rss/"

    def description(self, obj):
        return f"Latest published blog posts for {obj.company_name}"

    def items(self, obj):
        """Return only live (published) and public blog pages belonging to this company."""
        return (
            BlogPage.objects.filter(company=obj, live=True)
            .public()
            .order_by('-first_published_at', '-go_live_at', '-latest_revision_created_at')
        )

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        if item.short_description:
            return item.short_description
        if hasattr(item, 'body') and item.body:
            return strip_tags(str(item.body))[:300]
        return ""

    def item_pubdate(self, item):
        if item.first_published_at:
            return item.first_published_at
        if hasattr(item, 'publish_date') and item.publish_date:
            return item.publish_date
        return item.latest_revision_created_at

    def item_link(self, item):
        """Return absolute or full Wagtail page URL."""
        return item.full_url or item.url

    def item_enclosure_url(self, item):
        """Include the blog featured image in the RSS feed enclosure tag."""
        if item.featured_image:
            try:
                rendition = item.featured_image.get_rendition('fill-800x500')
                url = rendition.full_url or rendition.url
                if url and not url.startswith('http'):
                    url = f"http://127.0.0.1:8000{url}"
                return url
            except Exception:
                if hasattr(item.featured_image, 'file'):
                    url = item.featured_image.file.url
                    if url and not url.startswith('http'):
                        url = f"http://127.0.0.1:8000{url}"
                    return url
        return None

    def item_enclosure_length(self, item):
        if item.featured_image and hasattr(item.featured_image, 'file'):
            try:
                return item.featured_image.file.size
            except Exception:
                pass
        return 100000

    def item_enclosure_mime_type(self, item):
        if item.featured_image:
            return "image/jpeg"
        return None
