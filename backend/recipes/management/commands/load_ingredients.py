import json
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из файла ingredients.json'

    def handle(self, *args, **options):
        file_path = 'data/ingredients.json'

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                ingredients_data = json.load(file)

            created_count = 0
            skipped_count = 0

            for item in ingredients_data:
                try:
                    Ingredient.objects.create(
                        name=item['name'],
                        measurement_unit=item['measurement_unit']
                    )
                    created_count += 1
                except IntegrityError:
                    skipped_count += 1
                    continue

            self.stdout.write(
                self.style.SUCCESS(
                    f'Успешно загружено {created_count} ингредиентов. '
                    f'Пропущено {skipped_count} дубликатов.'
                )
            )

        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f'Файл {file_path} не найден!')
            )
        except KeyError as e:
            self.stdout.write(
                self.style.ERROR(f'Отсутствует ключ в JSON данных: {e}')
            )
        except json.JSONDecodeError:
            self.stdout.write(
                self.style.ERROR('Неверный формат JSON в файле!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Произошла ошибка: {e}')
            )
