from django.db.models import Sum
from django.http import HttpResponse

from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.pagination import LimitPagePagination
from recipes.models import (Favorites, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Subscription, User

from .filters import IngredientSearchFilter, RecipeSearchFilter
from .permissions import AnonimOrAuthenticatedReadOnly, IsAuthorOrReadOnly
from .serializers import (CustomUserSerializer, IngredientSerializer,
                          RecipeCreateSerializer, RecipeSerializer,
                          RecipeShortListSerializer, SubscriptionSerializer,
                          SubscriptionShowSerializer, TagSerializer)


class CustomUserViewSet(UserViewSet):
    """ВьюСет для создания/просмотра пользователей,
    создания/управления подписками."""

    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = LimitPagePagination
    permission_classes = (AnonimOrAuthenticatedReadOnly,)

    @action(
        detail=False,
        methods=['get', 'patch'],
        url_path='me',
        url_name='me',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def get_me(self, request):
        """Просмотр профиля пользователя."""

        if request.method == 'PATCH':
            serializer = CustomUserSerializer(
                request.user, data=request.data,
                partial=True, context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        serializer = CustomUserSerializer(
            request.user, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='subscribe',
        url_name='subscribe',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def get_subscribe(self, request, id):
        """Подписка/отписка пользователя на авторов."""

        subscriber = request.user
        author = get_object_or_404(User, id=id)
        change_subscription = Subscription.objects.filter(
            subscriber=subscriber.id, author=author.id
        )
        if request.method == 'POST':
            serializer = SubscriptionSerializer(
                data={'subscriber': request.user.id, 'author': author.id}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            author_serializer = SubscriptionShowSerializer(
                author, context={'request': request}
            )
            return Response(
                author_serializer.data, status=status.HTTP_201_CREATED
            )
        if change_subscription.exists():
            change_subscription.delete()
            return Response(f'Вы отписались от {author}',
                            status=status.HTTP_204_NO_CONTENT)
        return Response(f'Вы не подписаны на {author}',
                        status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['get'],
        url_path='subscriptions',
        url_name='subscriptions',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def get_subscriptions(self, request):
        """Получение подписок на авторов."""

        authors = User.objects.filter(author__subscriber=request.user)
        paginator = LimitOffsetPagination()
        result_pages = paginator.paginate_queryset(
            queryset=authors, request=request
        )
        serializer = SubscriptionShowSerializer(
            result_pages, context={'request': request}, many=True
        )
        return paginator.get_paginated_response(serializer.data)


class TagViewSet(ReadOnlyModelViewSet):
    """ВьюСет для тегов."""

    queryset = Tag.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(ReadOnlyModelViewSet):
    """ВьюСет для ингридиентов."""

    queryset = Ingredient.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientSearchFilter
    search_fields = ('^name', )


class RecipeViewSet(viewsets.ModelViewSet):
    """ВьюСет для создания рецепта."""

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = LimitPagePagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeSearchFilter
    permission_classes = (IsAuthorOrReadOnly,)

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeSerializer
        return RecipeCreateSerializer

    @action(
        detail=True,
        methods=['post'],
        url_path='favorite',
        url_name='favorite',
    )
    def favorite(self, request, pk):
        """Добавление и удаление рецепта в избранное."""
        serializer = RecipeShortListSerializer(
            data={'user': request.user.pk, 'recipe': pk}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        deleted_favorites, _ = Favorites.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted_favorites:
            return Response(
                {'errors': 'Рецепта нет в избранном!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post'],
        url_path='shopping_cart',
        url_name='shopping_cart',
    )
    def shopping_cart(self, request, pk):
        """Добавление и удаление рецепта в список покупок."""
        serializer = RecipeShortListSerializer(
            data={'user': request.user.pk, 'recipe': pk}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        deleted_shopping_list, _ = (
            ShoppingCart.objects.filter(user=request.user, recipe=recipe)
        ).delete()
        if not deleted_shopping_list:
            return Response(
                {'errors': 'Рецепта нет в списке покупок!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False)
    def download_shopping_cart(self, request):
        user = request.user
        filename = f'{user.username}_shopping_list.txt'
        ingredients = (RecipeIngredient.objects.filter(
            recipe__in=request.user.shopping_cart.all())
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total_amount=Sum('amount')))
        file_list = []
        for ingredient_data in ingredients:
            ingredient = ingredient_data['ingredient__name']
            amount = ingredient_data['total_amount']
            unit = ingredient_data['ingredient__measurement_unit']
            file_list.append(f'{ingredient} - {amount} {unit}.')

            file = HttpResponse('Cписок покупок:\n' + '\n'.join(file_list),
                                content_type='text/plain')
            file['Content-Disposition'] = f'attachment; filename="{filename}"'
        return file
