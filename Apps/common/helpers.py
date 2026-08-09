import secrets
import string


def generate_api_key(length=32):
    """
    Generate a secure random API key.
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_unique_slug(model, field_value, slug_field='slug'):
    """
    Generate a unique slug for a model instance.
    """
    from django.utils.text import slugify
    
    slug = slugify(field_value)
    original_slug = slug
    counter = 1
    
    while model.objects.filter(**{slug_field: slug}).exists():
        slug = f"{original_slug}-{counter}"
        counter += 1
    
    return slug
