# Multi-company Wagtail Blog Platform — Implementation Workflow

## Objective

Build a Wagtail CMS where the platform team can create companies and each company has:

- a separate, permission-protected Wagtail workspace for managing its content;
- a Wagtail-managed one-page website on its own domain;
- a blog area where staff create, review, publish, and unpublish posts; and
- an optional secure API for an external website to retrieve that company's published posts.

Wagtail is the source of truth for the website pages and blog posts. Do not build a second custom blog dashboard.

## 1. Confirm decisions before development

The employee should confirm these choices with the product owner before writing migrations:

1. Will each company use its own domain/subdomain, such as `acme.com` or `acme.platform.com`?
2. Should company managers be able to publish immediately, or should every post require approval by a platform administrator?
3. Is the API for an external website that already exists, or will Wagtail serve the website and blog directly?
4. Should categories and tags be shared globally or kept separate for each company? Recommended: company-specific.
5. What one-page website sections are required? Recommended initial sections: hero, about, services, testimonials, CTA, contact details, footer.

## 2. Target Wagtail page structure

Create one Wagtail Site and one page subtree per company.

```text
Wagtail root
└── Company Home Page (Company A, configured as a Wagtail Site root)
    ├── Blog Index
    │   ├── Blog Post: First post
    │   └── Blog Post: Second post
    └── Optional utility pages
```

Each company's Wagtail Site points at its own `CompanyHomePage`. This makes the one-page website and blog URLs resolve correctly for that company's domain.

## 3. Data model

Implement these models and relationships.

| Model | Purpose | Key fields |
| --- | --- | --- |
| `Company` | Tenant/workspace record | name, slug, domain, website URL, logo, status, API key |
| `CompanyMembership` | Connects users to a company | company, user, role (`manager`, `editor`) |
| `CompanyHomePage` | The one-page Wagtail website | one-to-one company, StreamField/section content, SEO fields |
| `BlogIndexPage` | Parent of a company's posts | company or company derived from the parent home page |
| `BlogPage` | A Wagtail blog post | title, slug, intro, body, image, author, category, tags, featured, SEO |
| `BlogCategory` / `BlogTag` | Blog taxonomy | company, name, slug, description where relevant |

Rules:

- Every blog post must belong to exactly one company.
- A blog post can only be created under that company's `BlogIndexPage`.
- Derive the company from the parent page in the Wagtail form; do not let editors select another company manually.
- Use Wagtail's `live` / revision / scheduled-publishing state as the publication source of truth. Do not maintain a second, independent `published` flag.

## 4. Tenant isolation and Wagtail permissions

This is the most important implementation phase.

1. When a platform administrator creates a company, create two Django/Wagtail groups:
   - `Company <name> Managers`: add, edit, publish within that company page subtree.
   - `Company <name> Editors`: add and edit within that subtree; cannot publish.
2. When a user is added to `CompanyMembership`, automatically add them to the matching group.
3. Apply Wagtail `GroupPagePermission` entries to the company home page or blog index so permissions inherit to all blog posts below it.
4. Add Wagtail hooks that:
   - only show the user's own company pages in the page explorer/search;
   - block direct URL access to another company's page;
   - prevent non-platform users from moving or copying posts between companies; and
   - restrict the Company field in Wagtail page forms.
5. Platform administrators remain superusers and can access all companies.

Acceptance check: an editor who changes a page ID in the Wagtail URL must receive a permission-denied response, not another company's content.

## 5. Wagtail dashboard experience

Add a custom panel to the existing Wagtail dashboard (`/cms/`), not a separate admin application.

Each assigned company gets its own dashboard card/section showing:

- company name and logo;
- number of published posts and drafts;
- most recently changed posts;
- **Open workspace** action, linking to that company's `BlogIndexPage`;
- **New blog post** action; and
- the read-only API endpoint/integration reminder.

For a user assigned to one company, only one workspace is visible. A platform administrator sees all companies. The Wagtail page explorer must still remain tenant-filtered; the dashboard is not the only security control.

## 6. One-page website implementation

Create `CompanyHomePage` as the company website's home page. Use Wagtail `StreamField` blocks so non-technical staff can reorder and edit sections.

Initial blocks:

- Hero: heading, description, CTA, image.
- Rich text / About.
- Services or feature cards.
- Testimonial cards.
- Blog preview: latest published posts from the current company's blog index.
- Contact / CTA.
- Footer details and social links.

Implement the page template and ensure the blog preview only queries posts belonging to the current company's page subtree/company.

## 7. Blog management workflow

1. Editor opens their company workspace in Wagtail.
2. Editor selects **New blog post**.
3. The post is automatically linked to the workspace company and the logged-in user is suggested as author.
4. Editor completes title, intro, feature image, rich content, category/tags, and SEO fields.
5. Editor saves a draft or submits it for review.
6. Manager reviews and publishes immediately or schedules the post.
7. Wagtail serves the live blog at the company's site URL; unpublished and scheduled content is never public.

If formal approvals are required, configure a Wagtail workflow on each company blog index. Editors submit; managers approve/publish. Do not attempt to reproduce this workflow outside Wagtail.

## 8. API workflow

The API is required only when a company has an external website that will display Wagtail-managed posts itself. If Wagtail serves the company website, use Wagtail page URLs/templates and treat the API as optional.

Required read endpoints:

```text
GET /api/v1/company/
GET /api/v1/blogs/
GET /api/v1/blogs/{slug}/
GET /api/v1/categories/
GET /api/v1/tags/
```

API rules:

- Authenticate with `X-API-Key` and resolve it to exactly one active company.
- Return only `BlogPage.objects.live().public()` posts belonging to that company.
- Support pagination, search, category, tag, featured, and ordering filters.
- Return title, slug, intro, body HTML/structured content, image URL, author, taxonomy, publish date, and SEO metadata.
- Scope categories and tags to the authenticated company.
- Return `401` for a missing/invalid key and `404` for a slug that does not exist in that company.
- Never put the API key into browser JavaScript. The company website must call the API from its server/backend or use Wagtail directly.

Provide Swagger/OpenAPI documentation and an example server-side request.

```bash
curl "https://cms.example.com/api/v1/blogs/?page_size=10" \
  -H "X-API-Key: COMPANY_SECRET_KEY"
```

## 9. Implementation order

| Phase | Employee deliverable | Review gate |
| --- | --- | --- |
| 1. Foundation | Environment, custom user model, Company and membership models | Migrations apply cleanly on an empty database |
| 2. Wagtail tenancy | Company Wagtail Site, homepage, blog index, inherited group permissions | Two test users cannot see or edit each other's content |
| 3. Content models | Blog page, images, taxonomy, SEO panels, one-page StreamField blocks | Manager can create and publish one post end-to-end |
| 4. Dashboard | Company workspace panel and scoped explorer | Editor sees only their own workspace and post counts |
| 5. Editorial workflow | Draft, approval (if needed), scheduling, previews | Editor cannot publish if their role does not allow it |
| 6. API | API-key auth, scoped endpoints, OpenAPI docs | Company A key never returns Company B data |
| 7. QA and security | Automated tests, accessibility check, deployment settings | All acceptance checks below pass |
| 8. Handover | Admin guide and API integration guide | Product owner can create a company without developer support |

## 10. Required automated tests

The employee must add tests for these cases before handoff:

- company creation generates a unique API key and workspace groups;
- membership assigns/removes the correct Wagtail group;
- a company's editor can create/edit only posts under their own blog index;
- a manager can publish; an editor cannot publish;
- the Wagtail explorer/dashboard does not list another company's blog pages;
- direct edit, publish, unpublish, move, copy, and delete URLs are blocked across tenants;
- API key authentication rejects missing, inactive, and invalid keys;
- a Company A API key returns only Company A live posts;
- API never returns drafts, scheduled posts, or Company B posts;
- the company home page blog preview displays only its own live posts.

## 11. Definition of done

The work is complete when:

- platform admin can create a company, domain/site, manager, and editor;
- the manager/editor log into `/cms/` and see only their company workspace;
- each company can manage its one-page website and its blog entirely in Wagtail;
- editors create drafts and managers publish them through Wagtail;
- each company domain shows only its own website/blog content;
- the optional API securely exposes only the authenticated company's live content;
- all tenancy and API tests pass; and
- there is a short admin setup guide covering company creation, member roles, domains, API key rotation, and backup/restore.

## Implementation notes for the employee

- Use Wagtail's page permissions and workflows wherever possible; avoid a parallel custom dashboard or blog CRUD system.
- Treat the database and Wagtail explorer filtering as defence in depth. UI filtering alone is not security.
- Use a real production database (PostgreSQL), HTTPS, secure environment variables, and restricted `ALLOWED_HOSTS` / CORS settings.
- Rotate API keys through a deliberate admin action and invalidate the previous key immediately.
- Keep the API read-only for the first version. Blog creation and publishing should remain in Wagtail, where revisions, previews, permissions, and workflows already exist.
