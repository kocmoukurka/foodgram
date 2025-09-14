from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from .constants import MINVALUE
from users.models import Subscribe
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
        fields = (
            'username',
            'id',
            'email',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )
        read_only_fields = ('id', 'is_subscribed')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        return (
            user
            and user.is_authenticated
            and obj.id != user.id
            and obj.subscribers.filter(user=user).exists()
        )


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
                    # Дополнительная проверка на положительное число
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

        if author.subscriptions.filter(user=user).exists():
            raise serializers.ValidationError(
                {'error': 'Вы уже подписаны на этого пользователя'}
            )

        return data

    def to_representation(self, instance):
        annotated_author = User.objects.filter(id=instance.author.id)\
            .annotate(recipes_count=Count('recipes')).first()
        return SubscriptionSerializer(
            annotated_author,
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
    amount = serializers.IntegerField(min_value=MINVALUE)


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
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    def get_image(self, obj):
        if obj.image:
            return self.context['request'].build_absolute_uri(obj.image.url)
        return ""


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Специализированный сериализатор для создания рецептов."""

    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    ingredients = IngredientInRecipeCreateSerializer(many=True)
    image = Base64ImageField(required=True,)
    cooking_time = serializers.IntegerField(min_value=MINVALUE)

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
        tag_ids = [tag.id for tag in value]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError(
                'Теги не должны повторяться.'
            )
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
        ingredient_objs = []
        for ingr in ingredients_data:
            ingredient_objs.append(
                IngredientInRecipe(
                    recipe=recipe,
                    ingredient_id=ingr['id'].id,
                    amount=ingr['amount']
                )
            )
        IngredientInRecipe.objects.bulk_create(ingredient_objs)

    @transaction.atomic
    def create(self, validated_data):
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        validated_data['author'] = self.context['request'].user

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self._create_ingredient_objects(recipe, ingredients_data)

        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        if 'tags' not in validated_data:
            raise serializers.ValidationError(
                {"tags": ["Это поле обязательно."]})
        if 'ingredients' not in validated_data:
            raise serializers.ValidationError(
                {"ingredients": ["Это поле обязательно."]})
        tags_data = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('ingredients', None)

        instance = super().update(instance, validated_data)

        if tags_data:
            instance.tags.set(tags_data)

        if ingredients_data:
            instance.recipe_ingredients.all().delete()
            self._create_ingredient_objects(instance, ingredients_data)

        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Упрощённый сериализатор для представления короткого вида рецепта."""
    
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

    def get_image(self, obj):
        """Возвращает абсолютный URL изображения."""

        return self.context.get('request').build_absolute_uri(
            obj.image.url) if obj.image else ''


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранных рецептов."""

    id = serializers.IntegerField(source='recipe.id', read_only=True)
    name = serializers.CharField(source='recipe.name', read_only=True)
    image = serializers.SerializerMethodField()
    cooking_time = serializers.IntegerField(
        source='recipe.cooking_time', read_only=True)

    class Meta:
        model = Favorite
        fields = ('id', 'name', 'image', 'cooking_time')

    def get_image(self, obj):
        if obj.recipe.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.recipe.image.url)
        return None


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок."""

    id = serializers.IntegerField(source='recipe.id', read_only=True)
    name = serializers.CharField(source='recipe.name', read_only=True)
    image = serializers.SerializerMethodField()
    cooking_time = serializers.IntegerField(
        source='recipe.cooking_time', read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ('id', 'name', 'image', 'cooking_time')

    def get_image(self, obj):
        if obj.recipe.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.recipe.image.url)
        return None


class AbstractUserRecipeCreateSerializer(serializers.ModelSerializer):
    """Абстрактный сериализатор без сложного representation."""

    error_message = 'Рецепт уже добавлен'

    class Meta:
        abstract = True
        fields = ('user', 'recipe')

    def validate(self, attrs):
        user = attrs.get('user')
        recipe = attrs.get('recipe')

        if self.Meta.model.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(self.error_message)

        return attrs

    def to_representation(self, instance):
        """Возвращаем только данные рецепта."""
        return ShortRecipeSerializer(
            instance.recipe,
            context=self.context
        ).data


class ShoppingCartCreateSerializer(AbstractUserRecipeCreateSerializer):
    """Сериализатор для создания записей в списке покупок.
    Наследует базовую логику валидации и преобразования.
    """

    error_message = 'Рецепт уже добавлен в список покупок'
    representation_serializer = ShoppingCartSerializer

    class Meta(AbstractUserRecipeCreateSerializer.Meta):
        model = ShoppingCart


class FavoriteCreateSerializer(AbstractUserRecipeCreateSerializer):
    """Сериализатор для создания записей в избранном.
    Наследует базовую логику валидации и преобразования.
    """

    error_message = 'Рецепт уже добавлен в избранное'
    representation_serializer = FavoriteSerializer

    class Meta(AbstractUserRecipeCreateSerializer.Meta):
        model = Favorite
