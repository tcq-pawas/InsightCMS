from django.test import TestCase
from django.contrib.auth.models import Group
from wagtail.models import Page, GroupPagePermission
from Apps.accounts.models import User
from Apps.companies.models import Company, CompanyHomePage, CompanyMembership
from Apps.companies.permissions import group_names_for_company, ensure_company_groups


class CompanyModelTest(TestCase):
    """Tests for the Company model itself, API keys, group provisioning, and membership sync."""

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

    def test_company_creation_generates_workspace_groups(self):
        # Company creation should automatically provision Manager and Editor groups
        company = Company.objects.create(
            company_name="Alpha Tech",
            website_name="Alpha",
            website_url="https://alpha.com",
            email="alpha@tech.com",
            contact_person="Alpha Guy",
            status="active",
        )
        manager_name, editor_name = group_names_for_company(company)
        self.assertTrue(Group.objects.filter(name=manager_name).exists())
        self.assertTrue(Group.objects.filter(name=editor_name).exists())

    def test_company_groups_page_permissions_attached(self):
        # Manager gets add/edit/publish while Editor gets only add/edit
        company = Company.objects.create(
            company_name="Beta Corp",
            website_name="Beta",
            website_url="https://beta.com",
            email="beta@corp.com",
            contact_person="Beta Guy",
            status="active",
        )
        root_page = Page.objects.filter(depth=2).first() or Page.objects.get(depth=1)
        home_page = CompanyHomePage(title="Beta Home", company=company)
        root_page.add_child(instance=home_page)
        home_page.save_revision().publish()

        manager_group, editor_group = ensure_company_groups(company)

        manager_perms = GroupPagePermission.objects.filter(group=manager_group, page=home_page)
        manager_codenames = [p.permission.codename for p in manager_perms]
        self.assertIn("add_page", manager_codenames)
        self.assertIn("change_page", manager_codenames)
        self.assertIn("publish_page", manager_codenames)

        editor_perms = GroupPagePermission.objects.filter(group=editor_group, page=home_page)
        editor_codenames = [p.permission.codename for p in editor_perms]
        self.assertIn("add_page", editor_codenames)
        self.assertIn("change_page", editor_codenames)
        self.assertNotIn("publish_page", editor_codenames)

    def test_membership_assigns_and_removes_correct_group(self):
        # Saving and deleting CompanyMembership should dynamically add/remove user from groups
        company = Company.objects.create(
            company_name="Gamma Services",
            website_name="Gamma",
            website_url="https://gamma.com",
            email="gamma@services.com",
            contact_person="Gamma Guy",
            status="active",
        )
        user = User.objects.create_user(
            email="employee@gamma.com",
            password="testpassword123",
            first_name="Test",
            last_name="User"
        )
        manager_name, editor_name = group_names_for_company(company)
        manager_group = Group.objects.get(name=manager_name)
        editor_group = Group.objects.get(name=editor_name)

        # 1. Add as Editor
        membership = CompanyMembership.objects.create(
            company=company,
            user=user,
            role=CompanyMembership.Role.EDITOR
        )
        user.refresh_from_db()
        self.assertIn(editor_group, user.groups.all())
        self.assertNotIn(manager_group, user.groups.all())

        # 2. Switch role to Manager
        membership.role = CompanyMembership.Role.MANAGER
        membership.save()
        user.refresh_from_db()
        self.assertIn(manager_group, user.groups.all())
        self.assertNotIn(editor_group, user.groups.all())

        # 3. Delete membership
        membership.delete()
        user.refresh_from_db()
        self.assertNotIn(manager_group, user.groups.all())
        self.assertNotIn(editor_group, user.groups.all())