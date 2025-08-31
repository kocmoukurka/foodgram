from django.contrib.auth.models import AbstractUser
from django.db import models

from users.constants import (
    MAX_EMAIL_LENGTH,
    MAX_FIRSTNAME_LENGTH,
    MAX_LASTNAME_LENGTH,
    MAX_USERNAME_LENGTH,
)
from users.validators import username_validator


class User(AbstractUser):
    """Кастомная модель пользователя."""

    username = models.CharField(
        verbose_name='Логин',
        max_length=MAX_USERNAME_LENGTH,
        unique=True,
        help_text=(
            'Обязательное поле. Не больше 150 символов. '
            'Только буквы, цифры и символы @/./+/-/_'
        ),
        validators=(username_validator,),
    )
    email = models.EmailField(
        verbose_name='Электронная почта',
        max_length=MAX_EMAIL_LENGTH,
        unique=True,
        help_text='Обязательное поле.',
    )
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=MAX_FIRSTNAME_LENGTH,
        blank=False,
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=MAX_LASTNAME_LENGTH,
        blank=False,
    )
    avatar = models.ImageField(
        blank=True,
        null=True,
        verbose_name='Аватар',
        help_text='Загрузите изображение профиля'
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username',)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('id',)

    def __str__(self):
        return self.username

    @property
    def subscribers(self):
        """Пользователи, которые подписаны на этого пользователя"""
        return User.objects.filter(subscriptions__following=self)

    @property
    def subscriptions(self):
        """Пользователи, на которых подписан этот пользователь"""
        return User.objects.filter(subscribers__user=self)


class Subscribe(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Кто подписался'
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='На кого подписался'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'following'),
                name='unique_follow'
            ),
        )
        ordering = ('user',)

    def __str__(self):
        return f'{self.user} подписался на {self.following}'
