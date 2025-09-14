from django.shortcuts import get_object_or_404, redirect

from .models import Recipe


def redirect_short_link(request, short_code):
    """Перенаправляет с короткой ссылки на страницу рецепта во фронтенде."""

    recipe = get_object_or_404(Recipe, short_link_code=short_code)

    return redirect(request.build_absolute_uri(f'/recipes/{recipe.id}/'))
