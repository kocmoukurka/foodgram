
from django import forms
import django_filters
from django_filters import ModelMultipleChoiceFilter

from recipes.models import Ingredient, Recipe, Tag


class RecipeFilter(django_filters.FilterSet):
    """Настройка фильтров для рецептов.
    Поддерживаются следующие фильтры:
    - Автор (автор рецепта)
    - Тэги (фильтрация по тэгам)
    - Избранные (показывать любимые рецепты пользователя)
    - Корзина (показывать рецепты в корзине пользователя)
    """

    author = django_filters.NumberFilter(field_name='author__id')
    tags = ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label='Теги'
    )
    is_favorited = django_filters.NumberFilter(method='filter_is_favorited')
    is_in_shopping_cart = django_filters.NumberFilter(
        method='filter_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ('author', 'tags',)

    def filter_tags(self, queryset, name, value):
        """Фильтрация по slug тегов."""

        tags_values = self.request.GET.getlist('tags') if hasattr(
            self, 'request') else []
        if tags_values:
            # Преобразуем названия в slug (если нужно)
            slug_values = [tag.lower().replace(
                ' ', '-') for tag in tags_values]
            return queryset.filter(tags__slug__in=slug_values).distinct()
        return queryset

    def filter_is_favorited(self, queryset, name, value):
        """Показывать только избранные рецепты конкретного пользователя.
        Возможные значения: 1 (включено), 0 (исключено).
        Примеры: /recipes/?is_favorited=1
        """

        user = getattr(self.request, 'user', None)
        if value and user and user.is_authenticated:
            value_int = int(value)
            if value_int == 1:
                return queryset.filter(favorite__user=user)
            elif value_int == 0:
                return queryset.exclude(favorite__user=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Показывать только рецепты, находящиеся в корзине пользователя.
        Возможные значения: 1 (включено), 0 (исключено).
        Примеры: /recipes/?is_in_shopping_cart=1
        """

        user = getattr(self.request, 'user', None)
        if value and user and user.is_authenticated:
            value_int = int(value)
            if value_int == 1:
                return queryset.filter(shoppingcart__user=user)
            elif value_int == 0:
                return queryset.exclude(shoppingcart__user=user)
        return queryset


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='istartswith'
    )

    class Meta:
        model = Ingredient
        fields = ('name',)
