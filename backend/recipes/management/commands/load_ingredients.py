import json

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из файла ingredients.json'

    def handle(self, *args, **options):
        file_path = 'data/ingredients.json'

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                ingredients_data = json.load(file)

            ingredients_to_create = []
            for item in ingredients_data:
                ingredients_to_create.append(
                    Ingredient(
                        name=item['name'],
                        measurement_unit=item['measurement_unit'])
                )

            created_count = Ingredient.objects.bulk_create(
                ingredients_to_create, ignore_conflicts=True)

            created_count = len(created_count)
            skipped_count = len(ingredients_data) - created_count

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
