from django.test import TestCase
from Apps.companies.models import Company


class CompanyModelTest(TestCase):
    """Tests for the Company model itself — not the API."""

    def test_api_key_auto_generated_on_create(self):
        # A new company should automatically get an API key
        company = Company.objects.create(
            company_name="Test Co",
            website_name="Test Site",
            website_url="https://test.com",
            email="test@test.com",
            contact_person="Test Person",
            status="active",
        )
        self.assertIsNotNone(company.api_key)
        self.assertNotEqual(company.api_key, "")

    def test_regenerate_api_key_changes_the_key(self):
        # Regenerating should produce a different key than before
        company = Company.objects.create(
            company_name="Test Co 2",
            website_name="Test Site",
            website_url="https://test2.com",
            email="test2@test.com",
            contact_person="Test Person",
            status="active",
        )
        old_key = company.api_key
        company.regenerate_api_key()
        self.assertNotEqual(old_key, company.api_key)

    def test_two_companies_never_share_the_same_api_key(self):
        # API keys must be unique across companies
        company_a = Company.objects.create(
            company_name="Company A",
            website_name="A Site",
            website_url="https://a.com",
            email="a@a.com",
            contact_person="A Person",
            status="active",
        )
        company_b = Company.objects.create(
            company_name="Company B",
            website_name="B Site",
            website_url="https://b.com",
            email="b@b.com",
            contact_person="B Person",
            status="active",
        )
        self.assertNotEqual(company_a.api_key, company_b.api_key)