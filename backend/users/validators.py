import re

from django.core.exceptions import ValidationError

from users.constants import ALLOWED_USERNAME_PATTERN


def username_validator(username):
    """Валидатор для проверки логина пользователя.
    Args:
        username (str): Проверяемый логин пользователя.
    Raises:
        ValidationError: Если логин не проходит валидацию.
    """

    invalid_chars = re.sub(ALLOWED_USERNAME_PATTERN, '', username)
    if invalid_chars:
        raise ValidationError(
            f'Недопустимые символы в логине {username}: '
            f'{"".join(set(invalid_chars))}. '
            'Разрешены только буквы, цифры и символы @/./+/-/_'
        )
    return username
