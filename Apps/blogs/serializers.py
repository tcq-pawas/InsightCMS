from rest_framework import serializers
from wagtail.images.models import Image
from Apps.blogs.models import BlogPage, BlogCategory, BlogTag


class ImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'title', 'width', 'height', 'url']

    def get_url(self, obj):
        try:
            return obj.get_rendition('width-800').url
        except Exception:
            return None


class BlogTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogTag
        fields = ['id', 'name', 'slug']


class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ['id', 'name', 'slug', 'description']


class BlogPageSerializer(serializers.ModelSerializer):
    featured_image = ImageSerializer(read_only=True)
    author_name = serializers.SerializerMethodField()
    category = BlogCategorySerializer(read_only=True)
    tags = BlogTagSerializer(many=True, read_only=True)
    company_name = serializers.SerializerMethodField()
    body_html = serializers.SerializerMethodField()

    class Meta:
        model = BlogPage
        fields = [
            'id', 'title', 'slug', 'featured_image', 'short_description',
            'body', 'body_html', 'author_name', 'category', 'tags', 'featured',
            'publish_date', 'company_name',
            'seo_title', 'search_description',
            'first_published_at', 'last_published_at',
        ]

    def get_author_name(self, obj):
        return obj.author.get_full_name() if obj.author else None

    def get_company_name(self, obj):
        return obj.company.company_name if obj.company else None

    def get_body_html(self, obj):
        return str(obj.body) if obj.body else ""


class BlogPageListSerializer(BlogPageSerializer):
    class Meta(BlogPageSerializer.Meta):
        fields = [
            'id', 'title', 'slug', 'featured_image', 'short_description',
            'author_name', 'category', 'tags', 'featured',
            'publish_date', 'company_name',
        ]