import base64
import hashlib
import secrets
import string

from django.conf import settings


def generate_short_link_code(recipe_id):
    """Генерирует уникальный короткий код для рецепта."""

    if recipe_id is None:
        # Для новых объектов генерируем полностью случайный код
        random_chars = secrets.choice(string.ascii_letters + string.digits)
        return ''.join(random_chars for _ in range(8))

    # Для существующих объектов используем детерминированную генерацию
    raw_data = f"{settings.SECRET_KEY}{recipe_id}".encode()
    hashed_data = hashlib.sha256(raw_data).digest()
    short_code = base64.urlsafe_b64encode(
        hashed_data[:6]).decode().replace('=', '')

    return short_code
