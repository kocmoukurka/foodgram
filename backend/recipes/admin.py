from django.forms import BaseInlineFormSet
from django.contrib import admin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from recipes.models import (
    Tag,
    Ingredient,
    Recipe,
    IngredientInRecipe,
    Favorite,
    ShoppingCart
)

admin.site.unregister(Group)


class IngredientInRecipeInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        has_valid_ingredients = False
        valid_forms_count = 0

        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE',
                                                               False):
                amount = form.cleaned_data.get('amount', 0)
                ingredient = form.cleaned_data.get('ingredient')

                if amount > 0 and ingredient is not None:
                    has_valid_ingredients = True
                    valid_forms_count += 1

        if not has_valid_ingredients:
            raise ValidationError(
                'Рецепт должен содержать хотя бы один ингредиент.'
            )

        if valid_forms_count == 0:
            raise ValidationError(
                'Добавьте хотя бы один ингредиент с количеством больше 0.'
            )


class IngredientInRecipeInline(admin.TabularInline):
    model = IngredientInRecipe
    extra = 1
    min_num = 1
    autocomplete_fields = ('ingredient',)
    formset = IngredientInRecipeInlineFormSet


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
    list_display = ('name', 'author', 'created', 'get_favorites_count')
    search_fields = ('name', 'author__username', 'tags__name')
    list_filter = ('tags', 'created')
    filter_horizontal = ('tags',)
    date_hierarchy = 'created'
    empty_value_display = '-пусто-'
    autocomplete_fields = ('author', 'tags')
    exclude = ('short_link_code',)
    inlines = (IngredientInRecipeInline,)

    def get_favorites_count(self, obj):
        return obj.favorites.count()
    get_favorites_count.short_description = 'В избранном'
    get_favorites_count.admin_order_field = 'favorites__count'

    def get_readonly_fields(self, request, obj=None):
        # Запрещаем изменение ID короткого линка после создания
        if obj:
            return ('id', 'created', 'short_link_code')
        return ()


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
