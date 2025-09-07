from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models import Count, Sum
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404, redirect
from djoser.views import UserViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
)
from rest_framework.viewsets import (
    GenericViewSet,
    ReadOnlyModelViewSet,
    ModelViewSet
)
from rest_framework import status

from users.models import Subscribe
from recipes.models import (
    Recipe,
    Ingredient,
    Tag,
    ShoppingCart,
    IngredientInRecipe,
    Favorite
)
from .serializers import (
    AvatarUpdateSerializer,
    TagSerializer,
    IngredientSerializer,
    UserSerializer,
    SubscriptionSerializer,
    RecipeCreateSerializer,
    RecipeSerializer,
    FavoriteSerializer,
    ShoppingCartSerializer,
)
from .filters import IngredientFilter, RecipeFilter
from .pagination import Pagination
from .permissions import IsAuthorOrReadOnly
from .mixins import AddRemoveObjectMixin, DownloadFileMixin

User = get_user_model()


def redirect_short_link(request, short_code):
    """
    Перенаправляет с короткой ссылки на страницу рецепта во фронтенде.
    """
    try:
        recipe = get_object_or_404(Recipe, short_link_code=short_code)
        return redirect(f'{settings.FRONTEND_URL}/recipes/{recipe.id}/')

    except Recipe.DoesNotExist:
        try:
            recipe_id = int(short_code, 36)
            recipe = get_object_or_404(Recipe, id=recipe_id)
            return redirect(f'{settings.FRONTEND_URL}/recipes/{recipe.id}/')
        except (ValueError, Recipe.DoesNotExist):
            return redirect(settings.FRONTEND_URL)


class RecipeViewSet(
    DownloadFileMixin,
    AddRemoveObjectMixin,
    ModelViewSet
):
    queryset = Recipe.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = Pagination
    permission_classes = (IsAuthorOrReadOnly,)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeCreateSerializer
        elif self.action == 'favorite':
            return FavoriteSerializer
        elif self.action == 'shopping_cart':
            return ShoppingCartSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_short_link(self, request, pk=None):
        base_url = request.build_absolute_uri('/')
        short_link = f'{base_url}s/{self.get_object().short_link_code}'
        return Response({'short-link': short_link})

    @action(methods=['post', 'delete'], detail=True, url_path='shopping_cart',
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user
        if request.method == 'POST':
            return self.add_to(ShoppingCart, user, recipe)
        elif request.method == 'DELETE':
            return self.remove_from(ShoppingCart, user, recipe)

    @action(methods=['get'], detail=False, url_path='download_shopping_cart',
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        shopping_list = IngredientInRecipe.objects.filter(
            recipe__shopping_carts__user=user
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount')).order_by('ingredient__name')

        if not shopping_list:
            return Response(
                {'error': 'Корзина покупок пуста'},
                status=status.HTTP_400_BAD_REQUEST
            )

        format_param = request.query_params.get('format', 'txt')
        return self.generate_file(shopping_list, user, format_param)

    @action(methods=['post', 'delete'], detail=True, url_path='favorite',
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user
        if request.method == 'POST':
            return self.add_to(Favorite, user, recipe)
        elif request.method == 'DELETE':
            return self.remove_from(Favorite, user, recipe)


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


class SubscribeViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated,)
    pagination_class = Pagination

    @action(methods=['post', 'delete'], detail=True, url_path='subscribe')
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, id=pk)
        user = request.user

        if request.method == 'POST':
            if user.id == author.id:
                return Response(
                    {'error': 'Нельзя подписаться на самого себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if Subscribe.objects.filter(user=user, following=author).exists():
                return Response(
                    {'error': 'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            Subscribe.objects.create(user=user, following=author)

            # ИСПРАВЛЕНИЕ: используем 'recipes' вместо 'recipe'
            annotated_author = User.objects.filter(id=author.id)\
                .annotate(recipes_count=Count('recipes')).first()

            serializer = SubscriptionSerializer(
                annotated_author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            subscription = Subscribe.objects.filter(
                user=user, following=author).first()

            if not subscription:
                return Response(
                    {'error': 'Вы не подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False, url_path='subscriptions')
    def subscriptions(self, request):
        # ИСПРАВЛЕНИЕ: используем 'recipes' вместо 'recipe'
        authors = User.objects.filter(
            subscribers__user=request.user
        ).annotate(
            # ИСПРАВЛЕНО: 'recipes' вместо 'recipe'
            recipes_count=Count('recipes')
            # ИСПРАВЛЕНО: 'recipes' вместо 'recipe_set'
        ).prefetch_related('recipes')

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


class DjoserUserViewSet(UserViewSet):
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'me':
            return [IsAuthenticated()]
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return super().get_permissions()

    @action(methods=['get', 'put', 'patch', 'delete'], detail=False,
            permission_classes=(IsAuthenticated,), url_path='me/avatar')
    def avatar(self, request):
        user = request.user

        if request.method == 'GET':
            return Response(
                {'avatar': user.avatar.url if user.avatar else None}
            )

        elif request.method in ['PUT', 'PATCH']:
            if 'avatar' not in request.data:
                return Response({'avatar': ['Это поле обязательно.']},
                                status=status.HTTP_400_BAD_REQUEST)
            serializer = AvatarUpdateSerializer(user, data=request.data,
                                                partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {'avatar': user.avatar.url if user.avatar else None}
                )
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
                user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
