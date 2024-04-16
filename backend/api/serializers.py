from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import IntegrityError
from django.db.models import F

from djoser.serializers import UserCreateSerializer, UserSerializer

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator

from users.models import Subscription, User

from utils.constans import (
    MAX_LENGTH, MAX_LENGTH_USER, MAX_VALUE, MIN_VALUE, RECIPES_LIMIT)
from utils.validators import validate_username

from .fields import Base64ImageField


class RecipeShortListSerializer(serializers.ModelSerializer):
    """Сериализатор для компактного отображения рецепта."""

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для создания пользователя."""

    username = serializers.CharField(
        required=True,
        max_length=MAX_LENGTH_USER,
        validators=[
            validate_username,
            UnicodeUsernameValidator()
        ]
    )

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'password',
        )

    def validate(self, data):
        """Валидация username и email на повторные названия."""

        if data.get('username') == 'me':
            raise serializers.ValidationError(
                'Нельзя использователь имя пользователя "me"'
            )
        if User.objects.filter(username=data.get('username')):
            raise serializers.ValidationError(
                'Пользователь с таким username уже существует'
            )
        if User.objects.filter(email=data.get('email')):
            raise serializers.ValidationError(
                'Пользователь с таким email уже существует'
            )
        return data


class CustomUserSerializer(UserSerializer):
    """Сериализатор для проверки подписки пользователя."""

    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        )

    def get_is_subscribed(self, object):
        """Проверка подписки пользователя на автора аккаунта."""

        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return object.author.filter(
            subscriber=request.user
        ).exists()


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Subscription."""

    class Meta:
        model = Subscription
        fields = (
            'subscriber',
            'author',
        )
        validators = [
            UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=('author', 'subscriber'),
                message='Вы уже подписывались на этого автора'
            )
        ]

    def validate(self, data):
        """Проверка, что пользователь не подписывается на самого себя."""
        if data['subscriber'] == data['author']:
            raise serializers.ValidationError(
                'Подписка на себя невозможна'
            )
        return data


class SubscriptionShowSerializer(CustomUserSerializer):
    """Сериализатор отображения подписок."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count'
        )

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.root.context.get('request')
        if request is not None:
            count = request.query_params.get('recipes_limit')
        else:
            count = self.root.context.get('recipes_limit')
        if count is not None:
            rep['recipes'] = rep['recipes'][:int(count)]
        return rep

    def get_recipes(self, object):
        author_recipes = object.recipes.all()[:RECIPES_LIMIT]
        return RecipeShortListSerializer(
            author_recipes, many=True
        ).data

    def get_recipes_count(self, object):
        return object.recipes.count()


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""

    class Meta:
        model = Tag
        fields = (
            'id',
            'name',
            'color',
            'slug',
        )
        read_only_fields = (
            'slug',
            'color'
        )


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингридиентов."""

    class Meta:
        model = Ingredient
        fields = (
            'id',
            'name',
            'measurement_unit',
        )


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов."""

    id = serializers.IntegerField(write_only=True)
    amount = serializers.IntegerField(write_only=True,
                                      max_value=MAX_VALUE,
                                      min_value=MIN_VALUE)

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'amount',
        )


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания рецепта."""

    name = serializers.CharField(max_length=MAX_LENGTH)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True)
    ingredients = RecipeIngredientSerializer(many=True)
    cooking_time = serializers.IntegerField(max_value=MAX_VALUE,
                                            min_value=MIN_VALUE)
    author = CustomUserSerializer(read_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        exclude = ('favorites', 'shopping_cart')

    def validate(self, data):
        """Проверка на обновление рецепта
        с несуществующим ингредиентом или тегом"""

        if 'ingredients' not in data:
            raise serializers.ValidationError(
                {'ingredients': ('Данного ингредиента еще нет.')}
            )
        if 'tags' not in data:
            raise serializers.ValidationError(
                {'tags', ('Данного тега еще нет.')}
            )
        return data

    def validate_ingredients(self, value):
        """Проверка на создание рецепта без поля и уникальности ингредиента"""

        if not value:
            raise serializers.ValidationError(
                ('Необходимо указать хотя бы один ингредиент')
            )
        ingredients_ids = [ingredient['id'] for ingredient in value]
        if len(ingredients_ids) != len(set(ingredients_ids)):
            raise serializers.ValidationError(
                ('Ингредиенты не должны повторяться.')
            )
        return value

    def validate_tags(self, value):
        """Проверка на создание рецепта без поля и уникальности тега"""

        if not value:
            raise serializers.ValidationError(
                ('Необходимо указать хотя бы один тег')
            )
        tags = [tag.id for tag in value]
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(('Теги не должны повторяться.'))
        return value

    def add_ingredients(self, recipe, ingredients):
        """Создание ингредиентов для рецепта"""

        try:
            RecipeIngredient.objects.bulk_create(
                RecipeIngredient(
                    recipe=recipe,
                    Ingredient_id=ingredient['id'],
                    amount=ingredient['amount'],
                )
                for ingredient in ingredients
            )
        except IntegrityError:
            raise ValidationError(
                ('Ошибка при добавлении ингредиента')
            )

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.add_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        super().update(instance, validated_data)
        instance.ingredients.clear()
        instance.tags.set(tags)
        self.add_ingredients(instance, ingredients)
        instance.save()
        return instance


class RecipeSerializer(RecipeCreateSerializer):
    """Сериализатор получения созданного рецепта"""

    tags = TagSerializer(read_only=True, many=True)
    ingredients = serializers.SerializerMethodField()
    name = serializers.CharField(max_length=MAX_LENGTH)
    author = CustomUserSerializer(read_only=True)
    image = Base64ImageField(allow_null=True)
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'ingredients',
            'name',
            'text',
            'cooking_time',
            'image',
            'author',
            'is_favorited',
            'is_in_shopping_cart'
        )

    def get_ingredients(self, obj):
        return obj.ingredients.values(
            'id',
            'name',
            'measurement_unit',
            amount=F('recipes_ingredients__amount'))

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return user.favorites.filter(pk=obj.pk).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return user.shopping_cart.filter(pk=obj.pk).exists()
        return False
