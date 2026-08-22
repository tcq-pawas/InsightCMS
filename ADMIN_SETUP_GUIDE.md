# InsightCMS - Administrator Setup & Operations Guide

This guide provides step-by-step instructions for platform administrators to set up companies, configure multi-tenancy, manage roles, rotate API keys, and perform backup & restore operations.

---

## 1. Company Creation

1. Log into the **Django Admin** at `/admin/` as a Platform Superuser.
2. Navigate to **Companies** > **Companies** > click **Add Company**.
3. Fill in the required details:
   - **Company Name**: Business display name (e.g., `Acme Corp`).
   - **Slug**: URL identifier (auto-generated or custom, e.g., `acme-corp`).
   - **Domain**: Target domain (e.g., `acme.example.com` or `acme.com`).
   - **Website Name & URL**: Marketing site details.
   - **Email & Contact Person**: Primary administrative contact.
   - **Status**: Set to `Active`.
4. Click **Save**.
   > **Note**: An API key is auto-generated immediately upon creation, and the matching Wagtail Django groups (`Company <Name> Managers` & `Company <Name> Editors`) are provisioned automatically.

---

## 2. Member Roles & User Assignment

Wagtail editorial access is governed through `CompanyMembership`:

| Role | Permissions |
|---|---|
| **Platform Superuser** | Full global access across all companies, settings, and pages. |
| **Manager** | Full control over their company's page tree: can **add, edit, and publish** pages. |
| **Editor** | Content creator for their company's tree: can **add and edit drafts only**; cannot publish. |

### Assigning a User to a Company:
1. In `/admin/`, navigate to **Companies** > **Company Memberships** > click **Add Company Membership**.
2. Select the **Company**, the **User**, and choose their **Role** (`Manager` or `Editor`).
3. Click **Save**. Group permissions sync dynamically.

---

## 3. Domain & Wagtail Site Mapping

- When a `CompanyHomePage` is created and assigned to a `Company`, a background signal automatically creates or updates the corresponding **Wagtail Site** entry (`wagtailcore.Site`).
- The hostname is automatically set to `Company.domain` and the root page points to the `CompanyHomePage`.
- **Custom Domains**: Simply update the `domain` field on the Company model in `/admin/` — the Wagtail Site record updates in real-time.

---

## 4. API Key Rotation

If an API key is compromised or needs periodic rotation:

### Via Django Admin:
1. Navigate to `/admin/` > **Companies** > **Companies**.
2. Select the company to open its change form.
3. Click the **Regenerate API Key** action / checkbox or trigger via Django shell.

### Via Django Shell:
```bash
python manage.py shell
```
```python
from Apps.companies.models import Company
company = Company.objects.get(slug="acme-corp")
company.regenerate_api_key()
print("New API Key:", company.api_key)
```
> **Security Note**: Once rotated, all external client applications must update their `X-API-Key` header immediately. Requests with the old key will receive `401 Unauthorized`.

---

## 5. Backup & Restore Operations

### Database Backup (PostgreSQL)

To create a complete database snapshot:
```bash
# Docker environment
docker-compose exec -T db pg_dump -U postgres insightcms_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Local environment
pg_dump -U postgres -h localhost -d insightcms_db -F c -b -v -f "backup_insightcms.dump"
```

### Media Files Backup
All uploaded images, logos, and Wagtail documents live in the `media/` directory:
```bash
tar -czvf media_backup_$(date +%Y%m%d_%H%M%S).tar.gz media/
```

---

### Restore Database & Media

#### 1. Restore Database:
```bash
# Docker environment
cat backup_YYYYMMDD_HHMMSS.sql | docker-compose exec -T db psql -U postgres -d insightcms_db

# Local environment
pg_restore -U postgres -h localhost -d insightcms_db -v "backup_insightcms.dump"
```

#### 2. Restore Media:
```bash
tar -xzvf media_backup_YYYYMMDD_HHMMSS.tar.gz -C .
```

#### 3. Post-Restore Verification:
```bash
python manage.py migrate
python manage.py test Apps.companies Apps.blogs -v2
```
