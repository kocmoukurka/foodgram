from django.contrib import admin
from django.contrib.auth.models import Group

from .models import (
    Favorite,
    Ingredient,
    IngredientInRecipe,
    Recipe,
    ShoppingCart,
    Tag,
)

admin.site.unregister(Group)


class IngredientInRecipeInline(admin.TabularInline):
    model = IngredientInRecipe
    extra = 1
    min_num = 1
    autocomplete_fields = ('ingredient',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', )
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('^name',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'created', 'get_favorite_count',
                    'get_tags', 'get_ingredients')
    search_fields = ('name', 'author__username', 'tags__name')
    list_filter = ('tags', 'created')
    filter_horizontal = ('tags',)
    date_hierarchy = 'created'
    empty_value_display = '-пусто-'
    autocomplete_fields = ('author', 'tags')
    exclude = ('short_link_code',)
    inlines = (IngredientInRecipeInline,)
    readonly_fields = ('short_link_code',)

    @admin.display(description='В избранном', ordering='favorite__count')
    def get_favorite_count(self, obj):
        return obj.favorite.count()

    @admin.display(description='Теги')
    def get_tags(self, obj):
        """
        Возвращает строку с тегами через запятую.
        """
        return ', '.join(tag.name for tag in obj.tags.all())

    @admin.display(description='Ингредиенты')
    def get_ingredients(self, obj):
        """
        Возвращает строку с ингредиентами через запятую.
        """
        return ', '.join(
            str(ingredient) for ingredient in obj.ingredients.all())


@admin.register(IngredientInRecipe)
class IngredientInRecipeAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name')
    autocomplete_fields = ('recipe', 'ingredient')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    autocomplete_fields = ('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    autocomplete_fields = ('user', 'recipe')
