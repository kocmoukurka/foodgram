from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Subscribe

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'recipes_count',
        'subscribers_count',
    )
    search_fields = ('username', 'email', 'first_name', 'last_name',)

    @admin.display(description='Рецептов')
    def recipes_count(self, obj):
        return obj.recipes.count()

    @admin.display(description='Подписчиков')
    def subscribers_count(self, obj):
        return obj.subscriptions.count()


@admin.register(Subscribe)
class SubscribeAdmin(admin.ModelAdmin):
    list_display = ('user', 'author',)
    search_fields = ('user__username', 'author__username',)
    list_filter = ('user', 'author',)
    ordering = ('user',)
