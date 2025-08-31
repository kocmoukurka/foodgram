import re

from django.core.exceptions import ValidationError

from .constants import ALLOWED_TAG_SLUG_PATTERN


def slug_validator(slug):
    invalid_chars = re.sub(ALLOWED_TAG_SLUG_PATTERN, '', slug)
    if invalid_chars:
        raise ValidationError(
            f'Недопустимые символы в логине {slug}: '
            f'{"".join(set(invalid_chars))}. '
            'Разрешены только буквы и цифры'
        )
    return slug
