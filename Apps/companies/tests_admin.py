from django.test import TestCase, RequestFactory
from django.core.exceptions import PermissionDenied
from wagtail.models import Page
from wagtail.test.utils import WagtailTestUtils

from Apps.accounts.models import User
from Apps.companies.models import Company, CompanyHomePage, CompanyMembership
from Apps.companies.permissions import ensure_company_groups
from Apps.companies.wagtail_hooks import (
    filter_explorer_by_company,
    block_cross_company_edit,
    block_cross_company_delete,
    block_cross_company_move,
    restrict_page_chooser_by_company,
)
from Apps.companies.dashboard import _companies_for_user
from Apps.blogs.models import BlogIndexPage, BlogPage


class WagtailAdminMultiTenancyTest(TestCase, WagtailTestUtils):
    """
    Tests covering Wagtail Admin tenant scoping, page explorer filtering,
    editorial publishing permissions, and cross-tenant action URL blocks.
    """

    def setUp(self):
        self.rf = RequestFactory()

        # Superuser
        self.superuser = User.objects.create_superuser(
            email="superadmin@platform.com",
            password="superpassword123",
            first_name="Super",
            last_name="Admin"
        )

        # Company A
        self.company_a = Company.objects.create(
            company_name="Company A",
            website_name="A Site",
            website_url="https://a.com",
            email="a@a.com",
            contact_person="A Person",
            status="active",
        )

        # Company B
        self.company_b = Company.objects.create(
            company_name="Company B",
            website_name="B Site",
            website_url="https://b.com",
            email="b@b.com",
            contact_person="B Person",
            status="active",
        )

        # Create Users
        self.editor_a = User.objects.create_user(
            email="editor_a@a.com",
            password="pass_editor_a",
            first_name="Editor",
            last_name="A",
            is_staff=True
        )
        self.manager_a = User.objects.create_user(
            email="manager_a@a.com",
            password="pass_manager_a",
            first_name="Manager",
            last_name="A",
            is_staff=True
        )

        # Assign memberships
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.editor_a,
            role=CompanyMembership.Role.EDITOR
        )
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.manager_a,
            role=CompanyMembership.Role.MANAGER
        )

        # Build Page Tree: Root -> CompanyHomePage -> BlogIndexPage -> BlogPage
        root_page = Page.objects.filter(depth=2).first() or Page.objects.get(depth=1)

        # Tree A
        self.home_a = CompanyHomePage(title="Home A", company=self.company_a)
        root_page.add_child(instance=self.home_a)
        self.home_a.save_revision().publish()

        self.blog_index_a = BlogIndexPage(title="Blog Index A")
        self.home_a.add_child(instance=self.blog_index_a)
        self.blog_index_a.save_revision().publish()

        self.post_a = BlogPage(
            title="Post A",
            short_description="Short A",
            body="<p>Content A</p>"
        )
        self.blog_index_a.add_child(instance=self.post_a)
        self.post_a.save_revision().publish()

        # Tree B
        self.home_b = CompanyHomePage(title="Home B", company=self.company_b)
        root_page.add_child(instance=self.home_b)
        self.home_b.save_revision().publish()

        self.blog_index_b = BlogIndexPage(title="Blog Index B")
        self.home_b.add_child(instance=self.blog_index_b)
        self.blog_index_b.save_revision().publish()

        self.post_b = BlogPage(
            title="Post B",
            short_description="Short B",
            body="<p>Content B</p>"
        )
        self.blog_index_b.add_child(instance=self.post_b)
        self.post_b.save_revision().publish()

        # Wire up permissions
        ensure_company_groups(self.company_a)
        ensure_company_groups(self.company_b)

    def test_explorer_shows_only_own_company_pages(self):
        """Wagtail explorer queryset me Editor A ko sirf Company A ke pages dikhne chahiye."""
        request = self.rf.get("/cms/pages/")
        request.user = self.editor_a

        all_pages = Page.objects.all()
        filtered_pages = filter_explorer_by_company(None, all_pages, request)

        self.assertIn(self.home_a.page_ptr, filtered_pages)
        self.assertIn(self.blog_index_a.page_ptr, filtered_pages)
        self.assertIn(self.post_a.page_ptr, filtered_pages)

        # Company B pages must not be included
        self.assertNotIn(self.home_b.page_ptr, filtered_pages)
        self.assertNotIn(self.blog_index_b.page_ptr, filtered_pages)
        self.assertNotIn(self.post_b.page_ptr, filtered_pages)

    def test_explorer_superuser_sees_all_companies(self):
        """Superuser ko dono companies ke pages dikhne chahiye."""
        request = self.rf.get("/cms/pages/")
        request.user = self.superuser

        all_pages = Page.objects.all()
        filtered_pages = filter_explorer_by_company(None, all_pages, request)

        self.assertIn(self.home_a.page_ptr, filtered_pages)
        self.assertIn(self.home_b.page_ptr, filtered_pages)

    def test_dashboard_shows_only_own_company(self):
        """Company A ke user ko sirf Company A dashboard card me dikhni chahiye."""
        companies_for_editor = _companies_for_user(self.editor_a)
        self.assertEqual(len(companies_for_editor), 1)
        self.assertEqual(companies_for_editor[0], self.company_a)

        companies_for_super = _companies_for_user(self.superuser)
        self.assertGreaterEqual(len(companies_for_super), 2)
        self.assertIn(self.company_a, companies_for_super)
        self.assertIn(self.company_b, companies_for_super)

    def test_manager_can_publish_and_editor_cannot(self):
        """Manager ke paas publish permission honi chahiye, Editor ke paas nahi."""
        perms_manager = self.blog_index_a.permissions_for_user(self.manager_a)
        perms_editor = self.blog_index_a.permissions_for_user(self.editor_a)

        self.assertTrue(perms_manager.can_publish())
        self.assertFalse(perms_editor.can_publish())

    def test_editor_cannot_edit_other_company_page(self):
        """Editor A agar Company B ke page ko edit karne ki koshish kare toh block hona chahiye."""
        request = self.rf.get(f"/cms/pages/{self.post_b.id}/edit/")
        request.user = self.editor_a

        with self.assertRaises(PermissionDenied):
            block_cross_company_edit(request, self.post_b)

    def test_editor_cannot_delete_other_company_page(self):
        """Editor A agar Company B ke page ko delete karne ki koshish kare toh block hona chahiye."""
        request = self.rf.post(f"/cms/pages/{self.post_b.id}/delete/")
        request.user = self.editor_a

        with self.assertRaises(PermissionDenied):
            block_cross_company_delete(request, self.post_b)

    def test_move_page_across_companies_is_blocked(self):
        """Post A ko Company B ke Blog Index ke under move karna block hona chahiye."""
        request = self.rf.post(f"/cms/pages/{self.post_a.id}/move/{self.blog_index_b.id}/")
        request.user = self.manager_a

        with self.assertRaises(PermissionDenied):
            block_cross_company_move(request, self.post_a, self.blog_index_b)

    def test_page_chooser_excludes_other_company_destinations(self):
        """Page chooser me Editor A ko sirf Company A ke pages destination me milne chahiye."""
        request = self.rf.get("/cms/choose-page/")
        request.user = self.editor_a

        all_pages = Page.objects.all()
        chooser_pages = restrict_page_chooser_by_company(all_pages, request)

        self.assertIn(self.home_a.page_ptr, chooser_pages)
        self.assertIn(self.blog_index_a.page_ptr, chooser_pages)
        self.assertNotIn(self.home_b.page_ptr, chooser_pages)
        self.assertNotIn(self.blog_index_b.page_ptr, chooser_pages)
