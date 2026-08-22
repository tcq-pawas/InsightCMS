from django.test import TestCase
from wagtail.models import Page
from Apps.companies.models import Company, CompanyHomePage
from Apps.blogs.models import BlogIndexPage, BlogPage


class BlogAPIIsolationTest(TestCase):
    """
    Most critical test: verifies that Company A's API key
    never returns Company B's data (tenant isolation).
    """

    def setUp(self):
        # Create two separate companies
        self.company_a = Company.objects.create(
            company_name="Company A",
            website_name="A Site",
            website_url="https://a.com",
            email="a@a.com",
            contact_person="A Person",
            status="active",
        )
        self.company_b = Company.objects.create(
            company_name="Company B",
            website_name="B Site",
            website_url="https://b.com",
            email="b@b.com",
            contact_person="B Person",
            status="active",
        )

        # Get the Wagtail root page (adjust if needed for your setup)
        root_page = Page.objects.filter(depth=2).first()

        # --- Set up Company A's page tree: HomePage -> BlogIndex -> BlogPage ---
        self.home_a = CompanyHomePage(title="Home A", company=self.company_a)
        root_page.add_child(instance=self.home_a)
        self.home_a.save_revision().publish()

        self.blog_index_a = BlogIndexPage(title="Blog A")
        self.home_a.add_child(instance=self.blog_index_a)
        self.blog_index_a.save_revision().publish()

        self.post_a = BlogPage(
            title="Post from Company A",
            short_description="Test",
            body="<p>Company A content</p>",
        )
        self.blog_index_a.add_child(instance=self.post_a)
        self.post_a.save_revision().publish()

        # --- Set up Company B's page tree: HomePage -> BlogIndex -> BlogPage ---
        self.home_b = CompanyHomePage(title="Home B", company=self.company_b)
        root_page.add_child(instance=self.home_b)
        self.home_b.save_revision().publish()

        self.blog_index_b = BlogIndexPage(title="Blog B")
        self.home_b.add_child(instance=self.blog_index_b)
        self.blog_index_b.save_revision().publish()

        self.post_b = BlogPage(
            title="Post from Company B",
            short_description="Test",
            body="<p>Company B content</p>",
        )
        self.blog_index_b.add_child(instance=self.post_b)
        self.post_b.save_revision().publish()

    def test_company_a_key_returns_only_company_a_posts(self):
        # Company A's key should only return Company A's posts
        response = self.client.get(
            "/api/v1/blogs/",
            HTTP_X_API_KEY=self.company_a.api_key,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        titles = [post["title"] for post in data["results"]]

        self.assertIn("Post from Company A", titles)
        self.assertNotIn("Post from Company B", titles)

    def test_company_b_key_returns_only_company_b_posts(self):
        # Company B's key should only return Company B's posts
        response = self.client.get(
            "/api/v1/blogs/",
            HTTP_X_API_KEY=self.company_b.api_key,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        titles = [post["title"] for post in data["results"]]

        self.assertIn("Post from Company B", titles)
        self.assertNotIn("Post from Company A", titles)

    def test_missing_api_key_returns_401(self):
        # Request without an API key should return 401
        response = self.client.get("/api/v1/blogs/")
        self.assertEqual(response.status_code, 401)

    def test_invalid_api_key_returns_401(self):
        # Request with an invalid API key should return 401
        response = self.client.get(
            "/api/v1/blogs/",
            HTTP_X_API_KEY="invalid-key-12345",
        )
        self.assertEqual(response.status_code, 401)

    def test_inactive_company_api_key_returns_401(self):
        # Inactive company's API key should be rejected with 401
        self.company_a.status = Company.Status.INACTIVE
        self.company_a.save()

        response = self.client.get(
            "/api/v1/blogs/",
            HTTP_X_API_KEY=self.company_a.api_key,
        )
        self.assertEqual(response.status_code, 401)

    def test_api_excludes_draft_and_unpublished_posts(self):
        # Draft posts (never published) must never be returned by API
        draft_post = BlogPage(
            title="Draft Post for Company A",
            short_description="Draft Description",
            body="<p>Draft Body</p>",
            live=False,
        )
        self.blog_index_a.add_child(instance=draft_post)
        draft_post.save_revision()  # Saved as draft only, NOT published

        # Published then unpublished post
        unpub_post = BlogPage(
            title="Unpublished Post for Company A",
            short_description="Unpublished Description",
            body="<p>Unpublished Body</p>",
        )
        self.blog_index_a.add_child(instance=unpub_post)
        unpub_post.save_revision().publish()
        unpub_post.unpublish()

        response = self.client.get(
            "/api/v1/blogs/",
            HTTP_X_API_KEY=self.company_a.api_key,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        titles = [post["title"] for post in data["results"]]

        self.assertIn("Post from Company A", titles)
        self.assertNotIn("Draft Post for Company A", titles)
        self.assertNotIn("Unpublished Post for Company A", titles)

    def test_wrong_slug_returns_404(self):
        # Request for a non-existent slug should return 404
        response = self.client.get(
            "/api/v1/blogs/wrong-slug-xyz/",
            HTTP_X_API_KEY=self.company_a.api_key,
        )
        self.assertEqual(response.status_code, 404)

    def test_company_a_cannot_access_company_b_post_detail(self):
        # Company A's key should not be able to fetch Company B's specific post
        response = self.client.get(
            f"/api/v1/blogs/{self.post_b.slug}/",
            HTTP_X_API_KEY=self.company_a.api_key,
        )
        self.assertEqual(response.status_code, 404)

    def test_blog_index_page_context_isolates_live_posts(self):
        # BlogIndexPage get_context only shows Company A's live posts
        draft_post = BlogPage(
            title="Company A Draft",
            short_description="Draft",
            body="<p>Draft</p>",
            live=False,
        )
        self.blog_index_a.add_child(instance=draft_post)
        draft_post.save_revision()

        context = self.blog_index_a.get_context(self.client.get("/").wsgi_request)
        context_blogs = list(context["blogs"])

        self.assertIn(self.post_a, context_blogs)
        self.assertNotIn(draft_post, context_blogs)
        self.assertNotIn(self.post_b, context_blogs)