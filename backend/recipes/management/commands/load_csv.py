
import csv

from django.conf import settings
from django.core.management.base import BaseCommand
from recipes.models import Ingredient, Tag
from tqdm import tqdm


class Command(BaseCommand):
    help = 'Загрузка CSV-файлов в базу данных.'

    def import_data(self, file_path, model, fields):
        if model.objects.all().exists():
            self.stdout.write(self.style.SUCCESS('Данные уже загружены.'))
        else:
            with open(file_path, 'r', encoding='utf8', newline='') as file:
                reader = csv.DictReader(file)
                total_items = sum(1 for _ in reader)
                for i, row in tqdm(enumerate(reader, 1), total=total_items,
                                   desc='Загрузка данных'):
                    self.stdout.write(f'Загрузка данных {i} из {total_items}',
                                      ending='\r')
                    obj, created = model.objects.get_or_create(
                        **{field: row[field] for field in fields})
                self.stdout.write(
                    self.style.SUCCESS('Данные успешно загружены!'))

    def handle(self, *args, **kwargs):
        self.import_data(
            file_path=settings.BASE_DIR / 'data/ingredients.csv',
            model=Ingredient,
            fields=['name', 'measurement_unit']
        )
        self.import_data(
            file_path=settings.BASE_DIR / 'data/tags.csv',
            model=Tag,
            fields=['name', 'color', 'slug']
        )
