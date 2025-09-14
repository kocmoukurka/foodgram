from io import BytesIO

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Exists, OuterRef
from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.urls import reverse
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
    SAFE_METHODS
)
from rest_framework.viewsets import (
    ReadOnlyModelViewSet,
    ModelViewSet
)
from rest_framework import status

from api.serializers import (
    AvatarUpdateSerializer,
    TagSerializer,
    IngredientSerializer,
    UserSerializer,
    SubscriptionSerializer,
    SubscribeSerializer,
    RecipeCreateSerializer,
    RecipeReadSerializer,
    ShoppingCartCreateSerializer,
    FavoriteCreateSerializer
)
from users.models import Subscribe
from recipes.models import (
    Recipe,
    Ingredient,
    Tag,
    ShoppingCart,
    IngredientInRecipe,
    Favorite
)
from api.filters import IngredientFilter, RecipeFilter
from api.pagination import Pagination
from api.permissions import IsAuthorOrReadOnly

User = get_user_model()


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.prefetch_related(
        'tags',
        'recipe_ingredients__ingredient',
        'author'
    ).select_related('author')
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = Pagination
    permission_classes = (IsAuthorOrReadOnly,)

    def generate_txt(self, items, user):
        """ Упрощенная версия генератора файла."""
        
        content = 'Список покупок:\n\n'
        content += '=' * 40 + '\n\n'

        for item in items:
            content += (f'• {item['ingredient__name']} - '
                        f'{item['total_amount']}'
                        f' {item['ingredient__measurement_unit']}\n')

        content += '\n' + '=' * 40 + '\n'
        content += f'Приятных покупок, {user.first_name or user.username}!'

        file_buffer = BytesIO(content.encode('utf-8'))
        file_buffer.seek(0)

        return FileResponse(
            file_buffer,
            content_type='text/plain; charset=utf-8',
            as_attachment=True,
            filename=f'shopping_list_{user.username}.txt'
        )

    def get_queryset(self):
        queryset = Recipe.objects.select_related(
            'author').prefetch_related('tags', 'ingredients',
                                       'recipe_ingredients__ingredient')

        if self.request.user.is_authenticated:
            user = self.request.user

            is_favorited = Favorite.objects.filter(
                user=user,
                recipe=OuterRef('pk')
            )

            is_in_shopping_cart = ShoppingCart.objects.filter(
                user=user,
                recipe=OuterRef('pk')
            )

            queryset = queryset.annotate(
                is_favorited=Exists(is_favorited),
                is_in_shopping_cart=Exists(is_in_shopping_cart)
            )

        return queryset

    def add_to_collection(self, create_serializer_class, pk):
        serializer = create_serializer_class(
            data={
                'user': self.request.user.id,
                'recipe': get_object_or_404(Recipe, pk=pk).id
            },
            context={'request': self.request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeCreateSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_short_link(self, request, pk=None):
        recipe = self.get_object()

        short_link = request.build_absolute_uri(
            reverse('short-link-redirect',
                    kwargs={'short_code': recipe.short_link_code})
        )

        return Response({'short-link': short_link})

    @action(methods=['get'], detail=False, url_path='download_shopping_cart',
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user

        # Получаем рецепты из корзины пользователя
        recipes_in_cart = Recipe.objects.filter(shoppingcart__user=user)

        # Получаем ингредиенты этих рецептов
        shopping_list = IngredientInRecipe.objects.filter(
            recipe__in=recipes_in_cart
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        if not shopping_list:
            return Response(
                {'error': 'Корзина покупок пуста'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return self.generate_txt(shopping_list, user)

    @action(methods=['post'], detail=True, url_path='shopping_cart',
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self.add_to_collection(
            create_serializer_class=ShoppingCartCreateSerializer, pk=pk)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        """ Удаляет рецепт из списка покупок пользователя."""

        try:
            Recipe.objects.get(id=pk)
            cart_item = ShoppingCart.objects.get(
                user=request.user,
                recipe_id=pk
            )
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Recipe.DoesNotExist:
            return Response(
                {"detail": "Рецепт не найден."},
                status=status.HTTP_404_NOT_FOUND
            )
        except ShoppingCart.DoesNotExist:
            return Response(
                {"detail":
                 "Данный рецепт отсутствует в вашем списке покупок."},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(methods=['post'], detail=True, url_path='favorite',
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        return self.add_to_collection(
            create_serializer_class=FavoriteCreateSerializer, pk=pk)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        """Удаляет рецепт из избранного пользователя."""

        try:
            Recipe.objects.get(id=pk)
            cart_item = Favorite.objects.get(
                user=request.user,
                recipe_id=pk
            )
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Recipe.DoesNotExist:
            return Response(
                {"detail": "Рецепт не найден."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Favorite.DoesNotExist:
            return Response(
                {"detail":
                 "Данный рецепт отсутствует в вашем списке покупок."},
                status=status.HTTP_400_BAD_REQUEST
            )


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filterset_class = IngredientFilter
    filter_backends = (DjangoFilterBackend,)
    pagination_class = None


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class UserViewSet(DjoserUserViewSet):
    serializer_class = UserSerializer
    permission_classes = (IsAuthorOrReadOnly,)
    pagination_class = Pagination

    def get_queryset(self):
        return User.objects.all()

    @action(["get", "put", "patch", "delete"],
            permission_classes=(IsAuthenticated,), detail=False)
    def me(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(methods=['get', 'put', 'patch'], detail=False,
            permission_classes=(IsAuthenticated,), url_path='me/avatar')
    def avatar(self, request):
        user = request.user
        serializer = AvatarUpdateSerializer(
            user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'avatar': user.avatar.url if user.avatar else None})

    @avatar.mapping.delete
    def delete_avatar(self, request):
        user = request.user
        user.avatar.delete(save=False)
        user.avatar = None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['post'], detail=True, url_path='subscribe')
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, pk=id)
        data = {'user': request.user.id, 'author': author.id}

        serializer = SubscribeSerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id=None):
        author = get_object_or_404(User, pk=id)
        user = request.user

        deleted_count, _ = Subscribe.objects.filter(
            user=user, author=author
        ).delete()

        if deleted_count:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'Вы не подписаны на этого пользователя'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(methods=['get'], detail=False, url_path='subscriptions')
    def subscriptions(self, request):
        authors = User.objects.filter(
            subscriptions__user=request.user
        ).annotate(
            recipes_count=Count('recipes')
        ).order_by('username')

        page = self.paginate_queryset(authors)
        if page is not None:
            serializer = SubscriptionSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = SubscriptionSerializer(
            authors,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
