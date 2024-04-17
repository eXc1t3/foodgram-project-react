from django.contrib import admin

from utils.constans import MIN_VALUE

from .models import Ingredient
from .models import Recipe
from .models import RecipeIngredient
from .models import Tag


class RecipeIngredientInline(admin.StackedInline):
    model = RecipeIngredient
    min_num = MIN_VALUE


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'favorites_count',)
    list_filter = ('name', 'author', 'tags',)
    inlines = [RecipeIngredientInline, ]

    def favorites_count(self, obj):
        return obj.favorites.count()


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    list_filter = ('name',)


admin.site.register(Tag)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(RecipeIngredient)
