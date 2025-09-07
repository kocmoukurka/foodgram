from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework import status


class AddRemoveObjectMixin:
    """
    Базовый миксин для добавления и удаления объектов в корзину и избранное.
    """

    def add_to(self, model, user, obj):
        """
        Метод для добавления объекта в базу данных.

        :param model: Класс модели (ShoppingCart или Favorite)
        :param user: Пользователь, выполняющий операцию
        :param obj: Объект, добавляемый в корзину или избранное
        :return: HTTP-ответ
        """
        if model.objects.filter(user=user, recipe=obj).exists():
            return Response(
                {'error': 'Элемент уже присутствует'},
                status=status.HTTP_400_BAD_REQUEST
            )
        new_instance = model.objects.create(user=user, recipe=obj)
        serializer = self.get_serializer(new_instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def remove_from(self, model, user, obj):
        """
        Метод для удаления объекта из базы данных.

        :param model: Класс модели (ShoppingCart или Favorite)
        :param user: Пользователь, выполняющий операцию
        :param obj: Объект, удаляемый из корзины или избранного
        :return: HTTP-ответ
        """
        instance = model.objects.filter(user=user, recipe=obj).first()
        if not instance:
            return Response(
                {'error': 'Элемента нет'},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DownloadFileMixin:
    """
    Миксин для формирования и отправки текстовых файлов.
    """

    def generate_file(self, items, user, fmt='txt'):
        """
        Формирует файл для скачивания (только TXT).

        :param items: Набор ингредиентов и количеств
        :param user: Текущий пользователь
        :param fmt: Формат файла (по умолчанию 'txt')
        :return: HTTP-ответ с файлом
        """
        return self.generate_txt(items, user)

    def generate_txt(self, items, user):
        """
        Генератор текстового файла.

        :param items: Ингредиенты и количества
        :param user: Пользователь
        :return: HTTP-ответ с файлом
        """
        response = HttpResponse(content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = (
            f'attachment; filename="'
            f'shopping_list_{user.username}'
            f'.txt"'
        )
        lines = [
            'Список покупок:',
            '\n',
            '=' * 40,
            '\n',
        ] + [
            f'• {item["ingredient__name"]} - '
            f'{item["total_amount"]} '
            f'{item["ingredient__measurement_unit"]}\n'
            for item in items
        ] + [
            '=' * 40,
            f'\nПриятных покупок, {user.first_name or user.username}!',
        ]
        response.write(''.join(lines))
        return response
