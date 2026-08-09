# InsightCMS

A centralized blog management system built with Django and Wagtail CMS that allows administrators to create and manage blog posts for multiple companies/websites. External websites can consume published blogs through secure REST APIs.

## Features

- **Multi-company blog management** - Manage blogs for multiple companies/websites
- **Company-specific blog ownership** - Each company has its own blog posts
- **Rich text editing** - Full-featured Wagtail editor with media support
- **Draft and published blog status** - Control blog publication workflow
- **Featured image upload** - Support for blog images and galleries
- **Categories and tags** - Organize blogs with categories and tags
- **Secure REST APIs** - Company-specific API access with API Key authentication
- **Wagtail media library** - Built-in image and document management
- **Blog search** - Full-text search across blog content
- **Pagination** - Efficient API responses with pagination
- **Responsive Wagtail admin** - Modern, mobile-friendly admin interface

## Technology Stack

- **Django** - Web framework
- **Wagtail CMS** - Content management system
- **Django REST Framework** - REST API framework
- **PostgreSQL** - Database
- **Docker** - Containerization
- **Bootstrap** - UI framework (for authentication pages)

## Project Structure

```
InsightCMS/
│
├── .github/
├── Apps/
│   ├── accounts/          # User management with custom user model
│   ├── companies/         # Company management with API key generation
│   ├── blogs/             # Wagtail blog pages and content
│   ├── api/               # REST API endpoints
│   └── common/            # Shared utilities and base models
│
├── docker/
├── InsightCMS/            # Django project settings
├── media/                 # User uploaded media files
├── static/                # Static files
├── staticfiles/           # Collected static files
├── templates/             # Django templates
│
├── manage.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env
├── example.env
└── README.md
```

## Installation

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Docker Setup (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd InsightCMS
```

2. Create environment file:
```bash
cp example.env .env
```

3. Update `.env` with your configuration:
```env
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_NAME=insightcms_db
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_HOST=db
DB_PORT=5432
```

4. Build and run with Docker Compose:
```bash
docker-compose up --build
```

5. Run migrations:
```bash
docker-compose exec web python manage.py migrate
```

6. Create a superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

7. Access the application:
- Wagtail Admin: http://localhost:8000/cms/
- Django Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/v1/

### Local Development Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up PostgreSQL database and update `.env` file

4. Run migrations:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## Usage

### Managing Companies

1. Access Django Admin at `/admin/`
2. Navigate to Companies section
3. Create a new company with:
   - Company Name
   - Website Name
   - Website URL
   - Email
   - Contact Person
   - Status (Active/Inactive)
4. The API Key will be auto-generated

### Managing Blogs

1. Access Wagtail Admin at `/cms/`
2. Navigate to Pages
3. Create a Blog Index page
4. Create Blog pages under the Blog Index
5. Fill in blog details:
   - Company (select the company)
   - Title
   - Featured Image
   - Short Description
   - Rich Text Content
   - Author
   - Category
   - Tags
   - Featured Blog
   - Status (Draft/Published)
   - Publish Date

### Managing Categories and Tags

1. Access Django Admin at `/admin/`
2. Navigate to Blog Categories or Blog Tags
3. Create categories and tags for organizing blogs

### API Usage

All API endpoints require API Key authentication via the `X-API-Key` header.

#### Endpoints

- **GET /api/v1/blogs/** - List published blogs for authenticated company
- **GET /api/v1/blogs/{slug}/** - Get a specific blog by slug
- **GET /api/v1/categories/** - List all categories
- **GET /api/v1/tags/** - List all tags
- **GET /api/v1/company/** - Get authenticated company details

#### Example Request

```bash
curl -X GET http://localhost:8000/api/v1/blogs/ \
  -H "X-API-Key: your-api-key-here"
```

#### Query Parameters

- **page** - Page number for pagination
- **page_size** - Number of items per page (max 100)
- **search** - Search blogs by title or description
- **category** - Filter by category ID
- **tags** - Filter by tag ID
- **featured** - Filter by featured status
- **ordering** - Order by field (e.g., publish_date, -publish_date)

#### Example with Filters

```bash
curl -X GET "http://localhost:8000/api/v1/blogs/?featured=true&page=1&page_size=10" \
  -H "X-API-Key: your-api-key-here"
```

## User Roles

### Super Admin
- Full access to all features
- Can manage users, companies, and all content
- Can access both Django Admin and Wagtail Admin

### Admin
- Can manage companies and content
- Can access both Django Admin and Wagtail Admin
- Cannot manage users

### Editor
- Can create and edit blog content
- Can only access Wagtail Admin
- Cannot manage companies or users

## Security

- API Key authentication for external access
- Company-specific data isolation
- Only published blogs accessible via API
- Secure password validation
- CSRF protection
- CORS configuration
- Security headers in production

## Development

### Running Tests

```bash
python manage.py test
```

### Creating Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Collecting Static Files

```bash
python manage.py collectstatic
```

## Production Deployment

1. Update `.env` with production settings:
```env
DEBUG=False
SECRET_KEY=your-secure-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

2. Use a production database (PostgreSQL recommended)

3. Configure static file serving (e.g., AWS S3, CloudFront)

4. Set up SSL/HTTPS

5. Configure email backend for notifications

6. Use a production WSGI server (Gunicorn recommended)

7. Set up process monitoring (Supervisor, systemd)

## License

This project is licensed under the MIT License.

## Support

For support and questions, please open an issue on the repository.
