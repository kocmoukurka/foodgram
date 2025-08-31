from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from djoser import views as djoser_views
from rest_framework.routers import DefaultRouter

from .views import (
    RecipeViewSet,
    TagViewSet,
    IngredientViewSet,
    DjoserUserViewSet,
    SubscribeViewSet,
)

router_v1 = DefaultRouter()
router_v1.register('recipes', RecipeViewSet, basename='recipes')
router_v1.register('tags', TagViewSet, basename='tags')
router_v1.register('ingredients', IngredientViewSet, basename='ingredients')
router_v1.register('users', SubscribeViewSet, basename='subscribe')

djoser_views.UserViewSet = DjoserUserViewSet

app_name = 'api'

urlpatterns = [
    path('', include(router_v1.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
