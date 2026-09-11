import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InsightCMS.settings")
django.setup()

from django.contrib.auth import get_user_model
from wagtail.models import Page, Site
from Apps.companies.models import Company, CompanyHomePage, CompanyBlogPostsPage
from Apps.blogs.models import BlogIndexPage, BlogPage, BlogCategory
from Apps.accounts.models import UserDashboardPage, LoginPage, RegisterPage

User = get_user_model()

print("1. Creating Superuser...")
admin_user = User.objects.filter(email="admin@example.com").first()
if not admin_user:
    admin_user = User.objects.create_superuser(
        email="admin@example.com",
        password="admin123",
        first_name="Shivangi",
        last_name="S",
        company_name="BlogPro"
    )
    print("   Created Superuser: admin@example.com / admin123")
else:
    admin_user.set_password("admin123")
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save()
    print("   Superuser updated: admin@example.com / admin123")

print("2. Creating Default Company...")
company, _ = Company.objects.get_or_create(
    company_name="BlogPro",
    defaults={
        "website_name": "BlogPro",
        "website_url": "https://blogpro.io",
        "email": "admin@blogpro.io",
        "contact_person": "Shivangi S",
        "status": "active",
        "api_key": __import__('secrets').token_hex(32),
    }
)

print("3. Setting up Wagtail Site & Home Page...")
root_page = Page.get_first_root_node()

# Remove Wagtail default placeholder home page if present
default_wagtail_home = Page.objects.filter(slug="home", depth=2).exclude(content_type__model="companyhomepage").first()
if default_wagtail_home:
    default_wagtail_home.delete()
    print("   Removed default Wagtail placeholder home page")

home_page = CompanyHomePage.objects.filter(slug="home").first()
if not home_page:
    home_page = CompanyHomePage(
        title="BlogPro",
        slug="home",
        brand_name="BlogPro",
        company=company,
        live=True
    )
    root_page.add_child(instance=home_page)
    print("   Created CompanyHomePage (/home)")
else:
    print("   CompanyHomePage already exists")

# Populate landing page StreamField blocks (Navbar & Body)
import json
home_page.brand_name = "BlogPro"
home_page.company = company

navbar_data = [
    {
        "type": "navbar",
        "value": {
            "nav_links": [
                {"label": "Home", "link_url": "#home"},
                {"label": "Features", "link_url": "#features"},
                {"label": "How It Works", "link_url": "#how-it-works"},
                {"label": "Subscription", "link_url": "#subscription"},
                {"label": "Contact", "link_url": "#contact"},
                {"label": "Blogs", "link_url": "/blog/"},
            ],
            "cta_text": "Get Started",
            "cta_link": "/login/",
            "logout_text": "Logout"
        }
    }
]

body_data = [
    {
        "type": "hero",
        "value": {
            "badge_text": "The Complete Blog Management Platform",
            "heading": "Write, Manage & Publish",
            "heading_highlight": "Power Your Content.",
            "description": "InsightCMS empowers creators and enterprise teams with an intuitive modern blogging engine, seamless publishing workflows, and unified workspace analytics.",
            "cta_text": "Get Started",
            "cta_link": "/login/",
            "secondary_cta_text": "View Dashboard",
            "secondary_cta_link": "/dashboard/",
            "subtext": "Create once. Publish everywhere.",
            "flow_cards": [
                {"title": "Editor", "subtitle": "Rich Text & Media", "icon_name": "pencil", "color_theme": "purple"},
                {"title": "Dashboard", "subtitle": "Workspace Stats", "icon_name": "grid", "color_theme": "blue"},
                {"title": "Publish", "subtitle": "Instant Live Blog", "icon_name": "paper-plane", "color_theme": "orange"},
                {"title": "Global", "subtitle": "Fast CDN & SEO", "icon_name": "globe", "color_theme": "pink"},
            ]
        }
    },
    {
        "type": "services",
        "value": {
            "heading": "Powerful Features For Modern Teams",
            "subheading": "Everything you need to grow your publication and audience.",
            "columns": "4",
            "cards": [
                {"title": "Rich Text Editing", "description": "Full-featured modern Quill editor with formatting, typography control, and instant image uploads."},
                {"title": "Workspace Management", "description": "Manage multi-tenant companies, author permissions, roles, and editorial review workflows."},
                {"title": "Audience Analytics", "description": "Gain actionable insights into visitor engagement, top performing articles, and referral traffic."},
                {"title": "SEO & Performance", "description": "Lightweight, pre-optimized static assets and clean responsive layouts built for speed."}
            ]
        }
    },
    {
        "type": "how_it_works",
        "value": {
            "heading": "How It Works",
            "steps": [
                {"step_number": 1, "title": "Create Workspace", "description": "Sign in and customize your company profile.", "icon_name": "dashboard"},
                {"step_number": 2, "title": "Draft & Edit", "description": "Write engaging stories with modern rich-media tools.", "icon_name": "paper-plane"},
                {"step_number": 3, "title": "Review & Publish", "description": "Publish instantly or schedule drafts for your audience.", "icon_name": "api"},
                {"step_number": 4, "title": "Grow Audience", "description": "Share stories with reader-ready layouts across all screens.", "icon_name": "globe"}
            ]
        }
    },
    {
        "type": "pricing",
        "value": {
            "heading": "Simple, Transparent Pricing",
            "subheading": "Choose the plan that fits your business scale.",
            "plans": [
                {
                    "plan_name": "Starter",
                    "description": "For individual writers & creators",
                    "price": "$19",
                    "period": "/month",
                    "features": ["1 Team Member", "Unlimited Blog Posts", "Standard Analytics", "Community Support"],
                    "button_text": "Start Free Trial",
                    "button_link": "/register/",
                    "is_featured": False
                },
                {
                    "plan_name": "Professional",
                    "description": "Best for growing companies & agencies",
                    "price": "$49",
                    "period": "/month",
                    "features": ["Up to 10 Editors", "Unlimited Blogs & Tags", "Advanced Audience Insights", "Priority Email Support", "Custom Branding"],
                    "button_text": "Get Started",
                    "button_link": "/register/",
                    "is_featured": True
                },
                {
                    "plan_name": "Enterprise",
                    "description": "Tailored for large organizations",
                    "price": "$99",
                    "period": "/month",
                    "features": ["Unlimited Team Members", "Custom API Integrations", "Dedicated Account Manager", "99.9% Uptime SLA"],
                    "button_text": "Contact Us",
                    "button_link": "#contact",
                    "is_featured": False
                }
            ]
        }
    },
    {
        "type": "contact_cta",
        "value": {
            "heading": "Ready to streamline your content operations?",
            "description": "Join modern publishing teams using BlogPro every day to scale their publications.",
            "button_text": "Get Started Now",
            "button_link": "/login/",
            "email": "support@blogpro.io",
            "phone": "+1 (555) 019-2834"
        }
    },
    {
        "type": "footer",
        "value": {
            "brand_name": "BlogPro",
            "company_description": "The unified modern blogging and content management platform for high-velocity teams.",
            "copyright_text": "(c) 2026 BlogPro Inc. All rights reserved.",
            "newsletter_heading": "Stay in the loop",
            "newsletter_text": "Get the latest updates, stories, and platform releases directly in your inbox.",
            "newsletter_placeholder": "Enter your business email",
            "social_links": [
                {"platform": "twitter", "url": "https://twitter.com"},
                {"platform": "linkedin", "url": "https://linkedin.com"},
                {"platform": "facebook", "url": "https://facebook.com"}
            ],
            "link_columns": [
                {
                    "heading": "Platform",
                    "links": [
                        {"label": "Home", "url": "#home"},
                        {"label": "Features", "url": "#features"},
                        {"label": "Pricing", "url": "#subscription"},
                        {"label": "Blogs", "url": "/blog/"}
                    ]
                },
                {
                    "heading": "Account",
                    "links": [
                        {"label": "Dashboard", "url": "/dashboard/"},
                        {"label": "Sign In", "url": "/login/"},
                        {"label": "Register", "url": "/register/"}
                    ]
                }
            ]
        }
    }
]

home_page.navbar = json.dumps(navbar_data)
home_page.body = json.dumps(body_data)
home_page.save_revision().publish()
print("   Populated CompanyHomePage StreamField blocks (Navbar, Hero, Services, Pricing, Footer)")

site = Site.objects.filter(is_default_site=True).first()
if not site:
    site = Site.objects.create(hostname="localhost", port=8000, root_page=home_page, is_default_site=True)
else:
    site.root_page = home_page
    site.save()
print(f"   Default Site configured -> Root: {home_page.title}")

print("4. Setting up BlogIndexPage under CompanyHomePage...")
blog_index = BlogIndexPage.objects.filter(slug="blog").first()
if not blog_index:
    blog_index = BlogIndexPage(
        title="Blog",
        slug="blog",
        subtitle="Explore our latest blog posts and articles.",
        live=True
    )
    home_page.add_child(instance=blog_index)
    blog_index.save_revision().publish()
    print("   Created BlogIndexPage (/blog/)")
else:
    print("   BlogIndexPage already exists")

print("5. Setting up Dashboard Pages...")
dashboard_page = UserDashboardPage.objects.filter(slug="dashboard").first()
if not dashboard_page:
    dashboard_page = UserDashboardPage(
        title="Dashboard",
        slug="dashboard",
        brand_name="BlogPro",
        welcome_heading="Dashboard",
        welcome_subtext="Welcome back! Here's what's happening with your blog.",
        live=True
    )
    sidebar_nav = [
        {"type": "link", "value": {"title": "Dashboard", "url": "/dashboard/", "icon": "fa-table-cells-large", "badge_text": "", "is_active": True}},
        {"type": "link", "value": {"title": "Posts", "url": "/blog-posts/", "icon": "fa-pen-nib", "badge_text": "", "is_active": False}},
        {"type": "link", "value": {"title": "Comments", "url": "/dashboard/#comment", "icon": "fa-comments", "badge_text": "", "is_active": False}},
        {"type": "link", "value": {"title": "Analytics", "url": "/dashboard/#overview", "icon": "fa-chart-line", "badge_text": "", "is_active": False}},
        {"type": "link", "value": {"title": "Settings", "url": "/settings/", "icon": "fa-gear", "badge_text": "", "is_active": False}},
        {"type": "link", "value": {"title": "Logout", "url": "/logout/", "icon": "fa-right-from-bracket", "badge_text": "", "is_active": False}}
    ]
    dashboard_page.sidebar_links = json.dumps(sidebar_nav)
    dashboard_page.new_post_button_text = "+ New Post"
    dashboard_page.new_post_button_url = "/dashboard/blogs/create/"
    home_page.add_child(instance=dashboard_page)
    dashboard_page.save_revision().publish()
    print("   Created UserDashboardPage (/dashboard/) with Sidebar Links")

blog_posts_page = CompanyBlogPostsPage.objects.filter(slug="blog-posts").first()
if not blog_posts_page:
    blog_posts_page = CompanyBlogPostsPage(
        title="Blog Posts",
        slug="blog-posts",
        page_heading="Blog Posts",
        page_subtext="Manage all blog posts across your workspace",
        live=True
    )
    home_page.add_child(instance=blog_posts_page)
    blog_posts_page.save_revision().publish()
    print("   Created CompanyBlogPostsPage (/blog-posts/)")

login_page = LoginPage.objects.filter(slug="login").first()
if not login_page:
    login_page = LoginPage(title="Login", slug="login", live=True)
    home_page.add_child(instance=login_page)
    login_page.save_revision().publish()
    print("   Created LoginPage (/login/)")

register_page = RegisterPage.objects.filter(slug="register").first()
if not register_page:
    register_page = RegisterPage(title="Register", slug="register", live=True)
    home_page.add_child(instance=register_page)
    register_page.save_revision().publish()
    print("   Created RegisterPage (/register/)")

print("6. Creating Sample Blog Post...")
category, _ = BlogCategory.objects.get_or_create(
    name="Technology",
    slug="technology",
    defaults={"company": company}
)

sample_post = BlogPage.objects.filter(slug="10-essential-ai-tools-2026").first()
if not sample_post:
    sample_post = BlogPage(
        title="10 Essential AI Tools Every Web Developer Should Use in 2026",
        slug="10-essential-ai-tools-2026",
        short_description="Discover top AI-driven tools that streamline full-stack development, boost coding productivity, and automate testing in modern workflows.",
        body="<p>Building modern web applications requires speed, precision, and high productivity. As AI capabilities continue to transform software engineering, developers are leveraging intelligent models to automate boilerplate code, optimize complex database queries, and streamline debugging.</p><p>Incorporating AI into your everyday workflow allows you to spend less time on repetitive manual tasks and focus on creating exceptional user experiences.</p>",
        category=category,
        company=company,
        author=admin_user,
        live=True
    )
    blog_index.add_child(instance=sample_post)
    sample_post.save_revision().publish()
    print("   Created Sample BlogPage")

print("\nSUCCESS! Database and all Wagtail pages recovered perfectly!")
