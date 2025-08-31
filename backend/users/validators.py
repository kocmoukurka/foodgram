import re

from django.core.exceptions import ValidationError

from users.constants import ALLOWED_USERNAME_PATTERN


def username_validator(username):
    """Валидатор для проверки логина пользователя.
    Проверяет:
    1. Что логин не равен 'me'.
    2. Что в логине не используются недопустимые символы.
    Args:
        username (str): Проверяемый логин пользователя.
    Raises:
        ValidationError: Если логин не проходит валидацию.
    """
    if username == 'me':
        raise ValidationError(
            f'Логин "{username}" запрещён.'
        )
    invalid_chars = re.sub(ALLOWED_USERNAME_PATTERN, '', username)
    if invalid_chars:
        raise ValidationError(
            f'Недопустимые символы в логине {username}: '
            f'{"".join(set(invalid_chars))}. '
            'Разрешены только буквы, цифры и символы @/./+/-/_'
        )
    return username
