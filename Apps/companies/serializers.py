from rest_framework import serializers
from Apps.companies.models import Company


class CompanySerializer(serializers.ModelSerializer):
    """Serializer for Company model."""
    
    class Meta:
        model = Company
        fields = [
            'id', 'company_name', 'website_name', 'website_url', 
            'logo', 'email', 'contact_person', 'status', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompanyDetailSerializer(CompanySerializer):
    """Detailed serializer for Company model."""
    
    class Meta(CompanySerializer.Meta):
        fields = CompanySerializer.Meta.fields + ['api_key']
