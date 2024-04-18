import json

from django.conf import settings
from django.core.management import BaseCommand

from recipes.models import Ingredient, Tag

# list_of_data = [
#     'ingredients',
#     'tags',
# ]

# data_models_dict = {
#     'ingredients': Ingredient,
#     'tags': Tag,
# }

class Command(BaseCommand):
    help = 'Загрузка JSON-файлов в базу данных.'

    def import_data(self, file_path, model, fields):
        if model.objects.all().exists():
            self.stdout.write(self.style.SUCCESS('Данные уже загружены.'))
        else:
            with open(file_path, 'r', encoding='utf8') as file:
                data = json.load(file)
                total_items = len(data)
                for i, item in enumerate(data, 1):
                    self.stdout.write(f'Загрузка данных {i} из {total_items}',
                                      ending='\r')
                    obj, created = model.objects.get_or_create(
                        **{field: item[field] for field in fields})
                self.stdout.write(
                    self.style.SUCCESS('Данные успешно загружены!'))

    def handle(self, *args, **kwargs):
        self.import_data(
            file_path=settings.BASE_DIR / 'data/ingredients.json',
            model=Ingredient,
            fields=['name', 'measurement_unit']
        )
        self.import_data(
            file_path=settings.BASE_DIR / 'data/tags.json',
            model=Tag,
            fields=['name', 'color', 'slug']
        )
