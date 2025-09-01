from django.contrib.auth import get_user_model
from django.db import models

from .constants import (
    MAX_TAG_NAME_SLUG_LENGTH,
    MAX_INGREDIENT_NAME_LENGTH,
    MAX_INGREDIENT_MEASUREMENT_UNIT_LENGTH,
    MAX_RECIPE_NAME_LENGTH,
)
from .validators import slug_validator

User = get_user_model()


class Tag(models.Model):
    """
    Модель представления тегов рецептов.
    """
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
        validators=(slug_validator,),
        help_text='Уникальная ссылка на тег.',
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        default_related_name = 'tags'
        ordering = ('name',)

    def __str__(self):
        """Строковое представление экземпляра."""
        return self.name


class Ingredient(models.Model):
    """
    Модель представления ингредиентов блюд.
    """
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
        default_related_name = 'ingredients'
        ordering = ('name',)

    def __str__(self):
        """Строковое представление экземпляра."""
        return self.name


class Recipe(models.Model):
    """
    Модель представления рецепта блюда.
    """
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
        help_text='Продолжительность готовки в минутах.',
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги',
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

    def __str__(self):
        """Строковое представление экземпляра."""
        return self.name


class IngredientInRecipe(models.Model):
    """
    Связывающая модель для связи рецепта с ингредиентом.
    """
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
    amount = models.PositiveIntegerField('Количество')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_ingredient_in_recipe'
            ),
        ]
        verbose_name = 'Связь Рецепт-Ингредиент'
        verbose_name_plural = 'Связи Рецепт-Ингредиенты'
        ordering = ('recipe',)

    def __str__(self):
        """Строковое представление экземпляра."""
        return f'Рецепт "{self.recipe}" включает {self.amount} ед. "{
            self.ingredient}"'


class Favorite(models.Model):
    """
    Избранные рецепты пользователей.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Рецепт в избранном',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'], name='unique_favorite'),
        ]
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные рецепты'
        ordering = ('user',)

    def __str__(self):
        """Строковое представление экземпляра."""
        return f'{self.user.username} добавил в избранное {self.recipe.name}'


class ShoppingCart(models.Model):
    """
    Список покупок пользователей.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_carts',
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_carts',
        verbose_name='Рецепт в списке покупок',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'], name='unique_shopping_cart'),
        ]
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        ordering = ('user',)

    def __str__(self):
        """Строковое представление экземпляра."""
        return f'{self.user.username} добавил в корзину {self.recipe.name}'
