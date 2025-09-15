from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

from .constants import (
    MAX_INGREDIENT_MEASUREMENT_UNIT_LENGTH,
    MAX_INGREDIENT_NAME_LENGTH,
    MAX_RECIPE_NAME_LENGTH,
    MAX_TAG_NAME_SLUG_LENGTH,
    MAX_NAME_RETURN,
    MIN_VALUE
)
from .services import generate_short_link_code

User = get_user_model()


class Tag(models.Model):
    """ Модель представления тегов рецептов."""

    name = models.CharField(
        'Название',
        max_length=MAX_TAG_NAME_SLUG_LENGTH,
        unique=True,
        help_text='Уникальное название тега.',
    )
    slug = models.SlugField(
        'Slug',
        max_length=MAX_TAG_NAME_SLUG_LENGTH,
        unique=True,
        help_text='Уникальная ссылка на тег.',
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        """Строковое представление экземпляра."""
        return self.name[:MAX_NAME_RETURN]


class Ingredient(models.Model):
    """ Модель представления ингредиентов блюд."""

    name = models.CharField(
        'Название',
        max_length=MAX_INGREDIENT_NAME_LENGTH,
        unique=True,
        help_text='Уникальное название ингредиента.',
    )
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=MAX_INGREDIENT_MEASUREMENT_UNIT_LENGTH,
        help_text='Тип единицы измерения (граммы, штуки и т.п.).',
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_ingredients'
            ),
        )
        ordering = ('name',)

    def __str__(self):
        """Строковое представление экземпляра."""
        return self.name[:MAX_NAME_RETURN]


class Recipe(models.Model):
    """ Модель представления рецепта блюда."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор',
    )
    name = models.CharField(
        'Название',
        max_length=MAX_RECIPE_NAME_LENGTH,
        help_text='Название рецепта.',
    )
    image = models.ImageField(
        'Изображение',
        upload_to='recipes/',
        help_text='Картинка рецепта.',
    )
    text = models.TextField('Описание', help_text='Описание рецепта.')
    cooking_time = models.PositiveIntegerField(
        'Время приготовления',
        validators=(MinValueValidator(MIN_VALUE),),
        help_text='Продолжительность готовки в минутах.',
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientInRecipe',
        related_name='recipes',
        verbose_name='Ингредиенты',
    )
    created = models.DateTimeField(
        'Дата создания',
        auto_now_add=True,
        help_text='Дата публикации рецепта.',
    )
    short_link_code = models.CharField(
        'Код короткой ссылки',
        max_length=10,
        blank=True,
        null=True,
        unique=True,
        help_text='Уникальный короткий код ссылки.',
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-created',)

    def save(self, *args, **kwargs):
        """
        Переопределенный метод сохранения для генерации короткой ссылки.
        """
        # Сохраняем сначала чтобы получить id
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Генерируем код только после сохранения
        if is_new and not self.short_link_code:
            self.short_link_code = generate_short_link_code(self.id)
            # Сохраняем снова с обновленным кодом
            super().save(update_fields=['short_link_code'])

    def __str__(self):
        """Строковое представление экземпляра."""
        return self.name[:MAX_NAME_RETURN]


class IngredientInRecipe(models.Model):
    """Связывающая модель для связи рецепта с ингредиентом."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Рецепт',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
    )
    amount = models.PositiveIntegerField(
        'Количество',
        validators=(MinValueValidator(MIN_VALUE),),
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_ingredient_in_recipe'
            ),
        )

        verbose_name = 'Связь Рецепт-Ингредиент'
        verbose_name_plural = 'Связи Рецепт-Ингредиенты'
        ordering = ('recipe',)

    def __str__(self):
        """Строковое представление экземпляра."""
        return (f'Рецепт "{self.recipe}" включает {self.amount} ед.'
                f'"{self.ingredient}"')


class AbstractUserRecipeRelation(models.Model):
    """Общая абстрактная модель для хранения отношения пользователя и рецепта.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='%(class)s',
        verbose_name='Рецепт',
    )

    class Meta:
        abstract = True
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_%(class)s'
            ),
        )
        ordering = ('user',)

    def __str__(self):
        """Форматированный вывод"""
        return (f'{self.user.username}'
                f'{self._meta.verbose_name.lower()} {self.recipe.name}')


class Favorite(AbstractUserRecipeRelation):
    """ Избранные рецепты пользователей."""

    class Meta(AbstractUserRecipeRelation.Meta):
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные рецепты'


class ShoppingCart(AbstractUserRecipeRelation):
    """ Списки покупок пользователей."""

    class Meta(AbstractUserRecipeRelation.Meta):
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
