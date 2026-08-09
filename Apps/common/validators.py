from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_image_extension(value):
    """
    Validate that the uploaded file is an image.
    """
    import os
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    if ext.lower() not in valid_extensions:
        raise ValidationError(_('Unsupported file extension. Allowed extensions are: %(extensions)s') % {'extensions': ', '.join(valid_extensions)})


def validate_document_extension(value):
    """
    Validate that the uploaded file is a document.
    """
    import os
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx']
    if ext.lower() not in valid_extensions:
        raise ValidationError(_('Unsupported file extension. Allowed extensions are: %(extensions)s') % {'extensions': ', '.join(valid_extensions)})
