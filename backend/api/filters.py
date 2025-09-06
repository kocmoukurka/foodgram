import django_filters
from recipes.models import Ingredient, Recipe


class RecipeFilter(django_filters.FilterSet):
    """
    Настройка фильтров для рецептов.
    Поддерживаются следующие фильтры:
    - Автор (автор рецепта)
    - Тэги (фильтрация по тэгам)
    - Избранные (показывать любимые рецепты пользователя)
    - Корзина (показывать рецепты в корзине пользователя)
    """

    tags = django_filters.CharFilter(method='filter_tags')
    author = django_filters.NumberFilter(field_name='author__id')
    is_favorited = django_filters.NumberFilter(method='filter_is_favorited')
    is_in_shopping_cart = django_filters.NumberFilter(
        method='filter_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ['author']

    def filter_tags(self, queryset, name, value):
        """
        Фильтрация рецептов по указанным тэгам.
        Параметр передается как список через GET-запрос.
        Примеры: /recipes/?tags=soup&tags=main_course
        """
        tags_values = self.data.getlist('tags') if hasattr(
            self, 'data') else []
        if tags_values:
            return queryset.filter(tags__slug__in=tags_values).distinct()
        return queryset

    def filter_is_favorited(self, queryset, name, value):
        """
        Показывать только избранные рецепты конкретного пользователя.
        Возможные значения: 1 (включено), 0 (исключено).
        Примеры: /recipes/?is_favorited=1
        """
        user = getattr(self.request, 'user', None)
        if value and user and user.is_authenticated:
            try:
                value_int = int(value)
                if value_int == 1:
                    return queryset.filter(favorites__user=user)
                elif value_int == 0:
                    return queryset.exclude(favorites__user=user)
            except (ValueError, TypeError):
                pass
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """
        Показывать только рецепты, находящиеся в корзине пользователя.
        Возможные значения: 1 (включено), 0 (исключено).
        Примеры: /recipes/?is_in_shopping_cart=1
        """
        user = getattr(self.request, 'user', None)
        if value and user and user.is_authenticated:
            try:
                value_int = int(value)
                if value_int == 1:
                    return queryset.filter(shopping_carts__user=user)
                elif value_int == 0:
                    return queryset.exclude(shopping_carts__user=user)
            except (ValueError, TypeError):
                pass
        return queryset


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name="name",
        lookup_expr='istartswith'
    )

    class Meta:
        model = Ingredient
        fields = ('name',)
