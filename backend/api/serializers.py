import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

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


class Base64ImageField(serializers.ImageField):
    """
    Серверизационное поле для изображений закодированных в base64.
    """

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format_, imgstr = data.split(';base64,')
            ext = format_.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(data)


class UserCreateSerializer(UserCreateSerializer):
    """
    Переопределённая версия стандартного сериализатора создания пользователя.
    """
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = (
            'username',
            'id',
            'email',
            'first_name',
            'last_name',
            'password'
        )
        read_only_fields = ('id', 'avatar',)
        extra_kwargs = {
            'password': {'write_only': True}
        }


class UserSerializer(UserSerializer):
    """
    Стандартный сериализатор пользователя с дополнительными полями.
    """
    is_subscribed = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'username',
            'id',
            'email',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes_count',
            'avatar',
        )
        read_only_fields = ('id', 'is_subscribed', 'recipes_count')

    def get_is_subscribed(self, obj):
        """
        Проверяет наличие подписки текущего пользователя на указанного автора.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if obj.id == request.user.id:
                return False
            return Subscribe.objects.filter(
                user=request.user,
                following=obj
            ).exists()
        return False


class SubscriptionSerializer(UserSerializer):
    """
    Сериализатор для отображения подписчиков с информацией о рецептах.
    """
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, obj):
        """
        Возврат списка рецептов автора с возможным ограничением по количеству.
        """
        request = self.context.get('request')
        recipes_limit = None
        if request and hasattr(request, 'query_params'):
            limit_str = request.query_params.get('recipes_limit')
            if limit_str and limit_str.isdigit():
                recipes_limit = int(limit_str)

        recipes = obj.recipes.all()
        if recipes_limit:
            recipes = recipes[:recipes_limit]

        return ShortRecipeSerializer(
            recipes, many=True, context=self.context).data


class AvatarUpdateSerializer(serializers.ModelSerializer):
    """
    Простой сериализатор для обновления аватара пользователя.
    """
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели тэгов.
    """
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели ингредиентов.
    """
    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для связи ингредиентов и рецептов.
    """
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = IngredientInRecipe
        fields = ['id', 'name', 'amount', 'measurement_unit']


class IngredientInRecipeCreateSerializer(serializers.Serializer):
    """
    Специальный сериализатор для ввода новых ингредиентов в рецепт.
    """
    id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)

    def validate_id(self, value):
        """
        Проверяет существование ингредиента по указанному ID.
        """
        if not Ingredient.objects.filter(id=value).exists():
            raise serializers.ValidationError("Ингредиент не существует.")
        return value


class RecipeSerializer(serializers.ModelSerializer):
    """
    Главный сериализатор для рецептов.
    """
    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True,
        source='recipe_ingredients',
        read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        ]

    def get_image(self, obj):
        """
        Вернуть абсолютный URL изображения рецепта.
        """
        if obj.image:
            return self.context['request'].build_absolute_uri(obj.image.url)
        return ""

    def get_is_favorited(self, obj):
        """
        Проверяет, находится ли рецепт в избранном у текущего пользователя.
        """
        if not isinstance(obj, Recipe):
            raise ValueError('Объект должен быть экземпляром Recipe.')
        user = self.context['request'].user
        if user.is_authenticated:
            return Favorite.objects.filter(user=user, recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        """
        Проверяет, находится ли рецепт в корзине покупок у текущего
        пользователя.
        """
        user = self.context['request'].user
        if user.is_authenticated:
            return ShoppingCart.objects.filter(user=user, recipe=obj).exists()
        return False


class RecipeCreateSerializer(serializers.ModelSerializer):
    """
    Специализированный сериализатор для создания рецептов.
    """
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    ingredients = IngredientInRecipeCreateSerializer(required=True, many=True)
    image = Base64ImageField(required=True)
    cooking_time = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recipe
        fields = [
            'tags', 'ingredients', 'image',
            'name', 'text', 'cooking_time'
        ]

    def validate_tags(self, value):
        """
        Дополнительная валидация тегов: обязательность и уникальность.
        """
        if not value:
            raise serializers.ValidationError(
                "Необходимо указать хотя бы один тег."
            )
        tag_ids = [tag.id for tag in value]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError(
                "Теги не должны повторяться."
            )
        return value

    def validate_ingredients(self, value):
        """
        Дополнительная валидация ингредиентов: обязательность и уникальность.
        """
        if not value:
            raise serializers.ValidationError(
                "Необходимо указать хотя бы один ингредиент."
            )
        ingredient_ids = [item['id'] for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                "Ингредиенты не должны повторяться."
            )
        return value

    def create(self, validated_data):
        """
        Создание рецепта вместе с соответствующими ингредиентами и тегами.
        """
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        validated_data['author'] = self.context['request'].user

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        ingredient_objs = []
        for ingr in ingredients_data:
            ingredient_objs.append(
                IngredientInRecipe(
                    recipe=recipe,
                    ingredient_id=ingr['id'],
                    amount=ingr['amount']
                )
            )
        IngredientInRecipe.objects.bulk_create(ingredient_objs)

        return recipe

    def update(self, instance, validated_data):
        """
        Обновление рецепта с заменой тегов и ингредиентов.
        """
        tags_data = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('ingredients', None)

        if self.context['request'].method == 'PUT' or self.context[
                'request'].method == 'PATCH':
            if tags_data is None:
                raise serializers.ValidationError({"tags": ["Обязательно."]})
            if ingredients_data is None:
                raise serializers.ValidationError(
                    {"ingredients": ["Обязательно."]})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            ingredient_objs = []
            for ingr in ingredients_data:
                ingredient_objs.append(
                    IngredientInRecipe(
                        recipe=instance,
                        ingredient_id=ingr['id'],
                        amount=ingr['amount']
                    )
                )
            IngredientInRecipe.objects.bulk_create(ingredient_objs)

        return instance

    def to_representation(self, instance):
        """
        После успешного сохранения возвращаем объект в полном представлении.
        """
        instance = Recipe.objects.prefetch_related(
            'tags',
            'recipe_ingredients__ingredient'
        ).get(id=instance.id)
        return RecipeSerializer(instance, context=self.context).data


class ShortRecipeSerializer(serializers.ModelSerializer):
    """
    Упрощённый сериализатор для представления короткого вида рецепта.
    """
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

    def get_image(self, obj):
        """
        Возвращает абсолютный URL изображения.
        """
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class FavoriteSerializer(serializers.ModelSerializer):
    """
    Сериализатор для избранных рецептов.
    """
    id = serializers.IntegerField(source='recipe.id', read_only=True)
    name = serializers.CharField(source='recipe.name', read_only=True)
    image = serializers.SerializerMethodField()
    cooking_time = serializers.IntegerField(
        source='recipe.cooking_time', read_only=True)

    class Meta:
        model = Favorite
        fields = ['id', 'name', 'image', 'cooking_time']

    def get_image(self, obj):
        """
        Возвращает абсолютный URL изображения рецепта.
        """
        if obj.recipe.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.recipe.image.url)
        return None


class ShoppingCartSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка покупок.
    """
    id = serializers.IntegerField(source='recipe.id', read_only=True)
    name = serializers.CharField(source='recipe.name', read_only=True)
    image = serializers.SerializerMethodField()
    cooking_time = serializers.IntegerField(
        source='recipe.cooking_time', read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ['id', 'name', 'image', 'cooking_time']

    def get_image(self, obj):
        """
        Возвращает абсолютный URL изображения рецепта.
        """
        if obj.recipe.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.recipe.image.url)
        return None
