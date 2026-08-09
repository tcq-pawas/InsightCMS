from rest_framework import serializers
from wagtail.images.models import Image
from Apps.blogs.models import BlogPage, BlogCategory, BlogTag


class ImageSerializer(serializers.ModelSerializer):
    """Serializer for Wagtail images."""
    
    class Meta:
        model = Image
        fields = ['id', 'title', 'file', 'width', 'height', 'url']


class BlogTagSerializer(serializers.ModelSerializer):
    """Serializer for BlogTag model."""
    
    class Meta:
        model = BlogTag
        fields = ['id', 'name', 'slug']


class BlogCategorySerializer(serializers.ModelSerializer):
    """Serializer for BlogCategory model."""
    
    class Meta:
        model = BlogCategory
        fields = ['id', 'name', 'slug', 'description']


class BlogPageSerializer(serializers.ModelSerializer):
    """Serializer for BlogPage model."""
    
    featured_image = ImageSerializer(read_only=True)
    author_name = serializers.SerializerMethodField()
    category = BlogCategorySerializer(read_only=True)
    tags = BlogTagSerializer(many=True, read_only=True)
    company_name = serializers.SerializerMethodField()
    
    class Meta:
        model = BlogPage
        fields = [
            'id', 'title', 'slug', 'featured_image', 'short_description',
            'body', 'author_name', 'category', 'tags', 'featured',
            'status', 'publish_date', 'company_name'
        ]
        read_only_fields = ['id']

    def get_author_name(self, obj):
        return obj.author.get_full_name() if obj.author else None

    def get_company_name(self, obj):
        return obj.company.company_name if obj.company else None


class BlogPageListSerializer(BlogPageSerializer):
    """Lightweight serializer for blog list views."""
    
    class Meta(BlogPageSerializer.Meta):
        fields = [
            'id', 'title', 'slug', 'featured_image', 'short_description',
            'author_name', 'category', 'tags', 'featured',
            'status', 'publish_date', 'company_name'
        ]
