from django.contrib.auth import get_user_model
from django.db import transaction
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from users.models import Subscribe
from recipes.constants import MIN_VALUE
from recipes.models import (
    Recipe,
    Tag,
    Ingredient,
    IngredientInRecipe,
    Favorite,
    ShoppingCart
)

User = get_user_model()


class UserSerializer(UserSerializer):
    """Стандартный сериализатор пользователя с дополнительными полями."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta(UserSerializer.Meta):
        model = User
        fields = UserSerializer.Meta.fields + ('is_subscribed', 'avatar')
        read_only_fields = ('id', 'is_subscribed')

    def get_is_subscribed(self, obj):
        """Проверяет, подписан ли текущий пользователь на этого автора."""

        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user_subscriptions.filter(user=request.user).exists()
        return False


class SubscriptionSerializer(UserSerializer):
    """Сериализатор для отображения подписчиков с информацией о рецептах."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True, default=0)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = None

        if request and hasattr(request, 'query_params'):
            limit_str = request.query_params.get('recipes_limit')
            if limit_str:
                try:
                    recipes_limit = int(limit_str)
                    if recipes_limit <= 0:
                        recipes_limit = None
                except (ValueError, TypeError):
                    recipes_limit = None

        recipes = obj.recipes.all()
        if recipes_limit:
            recipes = recipes[:recipes_limit]

        return ShortRecipeSerializer(
            recipes, many=True, context=self.context).data


class SubscribeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания подписок."""

    class Meta:
        model = Subscribe
        fields = ('user', 'author')

    def validate(self, data):
        user = data['user']
        author = data['author']
        if user == author:
            raise serializers.ValidationError(
                {'error': 'Нельзя подписаться на самого себя'}
            )

        if author.subscriptions_author.filter(user=user).exists():
            raise serializers.ValidationError(
                {'error': 'Вы уже подписаны на этого пользователя'}
            )

        return data

    def to_representation(self, instance):
        return SubscriptionSerializer(
            instance.author,
            context=self.context
        ).data


class AvatarUpdateSerializer(serializers.ModelSerializer):
    """Простой сериализатор для обновления аватара пользователя."""

    avatar = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = ('avatar',)

    def validate(self, data):
        if 'avatar' not in data:
            raise serializers.ValidationError(
                {'avatar': ['Это поле обязательно.']}
            )
        return data


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели тэгов."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug',)


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit',)


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для связи ингредиентов и рецептов."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'name', 'amount', 'measurement_unit')


class IngredientInRecipeCreateSerializer(serializers.Serializer):
    """ Специальный сериализатор для ввода новых ингредиентов в рецепт."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=MIN_VALUE)


class RecipeReadSerializer(serializers.ModelSerializer):
    """Главный сериализатор для рецептов."""

    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True,
        source='recipe_ingredients',
        read_only=True
    )
    is_favorited = serializers.BooleanField(read_only=True, default=False)
    is_in_shopping_cart = serializers.BooleanField(read_only=True,
                                                   default=False)
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Специализированный сериализатор для создания рецептов."""

    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    ingredients = IngredientInRecipeCreateSerializer(many=True)
    image = Base64ImageField(required=True,)
    cooking_time = serializers.IntegerField(min_value=MIN_VALUE)

    class Meta:
        model = Recipe
        fields = (
            'tags', 'ingredients', 'image',
            'name', 'text', 'cooking_time'
        )

    def validate_image(self, value):
        """Валидация для поля image."""

        if not value:
            raise serializers.ValidationError(
                'Изображение обязательно для заполнения.')
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError(
                'Необходимо указать хотя бы один тег.'
            )

        seen_ids = set()
        for tag in value:
            if tag.id in seen_ids:
                raise serializers.ValidationError(
                    'Теги не должны повторяться.'
                )
            seen_ids.add(tag.id)

        return value

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'Необходимо указать хотя бы один ингредиент.'
            )
        ingredient_ids = [item['id'] for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.'
            )
        return value

    @staticmethod
    def _create_ingredient_objects(recipe, ingredients_data):
        """Создание объектов ингредиентов с использованием генератора."""

        IngredientInRecipe.objects.bulk_create(
            IngredientInRecipe(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            ) for ingredient in ingredients_data
        )

    @transaction.atomic
    def create(self, validated_data):
        """Создание рецепта с ингредиентами и тегами."""
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(
            **validated_data
        )

        recipe.tags.set(tags_data)
        self._create_ingredient_objects(recipe, ingredients_data)

        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        """Обновление рецепта."""

        tags_data = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('ingredients', None)

        if tags_data:
            instance.tags.set(tags_data)

        if ingredients_data:
            instance.recipe_ingredients.all().delete()
            self._create_ingredient_objects(instance, ingredients_data)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Упрощённый сериализатор для представления короткого вида рецепта."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class AbstractUserRecipeCreateSerializer(serializers.ModelSerializer):
    """Абстрактный сериализатор без сложного representation."""

    class Meta:
        abstract = True
        fields = ('user', 'recipe')

    def validate(self, attrs):
        user = attrs.get('user')
        recipe = attrs.get('recipe')

        if self.Meta.model.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                f'{self.Meta.model._meta.verbose_name.capitalize()}'
                f' уже добавлено.'
            )

        return attrs

    def to_representation(self, instance):
        return ShortRecipeSerializer(
            instance.recipe,
            context=self.context
        ).data


class ShoppingCartCreateSerializer(AbstractUserRecipeCreateSerializer):
    """Сериализатор для создания записей в списке покупок.
    Наследует базовую логику валидации и преобразования.
    """

    class Meta(AbstractUserRecipeCreateSerializer.Meta):
        model = ShoppingCart


class FavoriteCreateSerializer(AbstractUserRecipeCreateSerializer):
    """Сериализатор для создания записей в избранном.
    Наследует базовую логику валидации и преобразования.
    """

    class Meta(AbstractUserRecipeCreateSerializer.Meta):
        model = Favorite
