from rest_framework.pagination import PageNumberPagination
from utils.constans import MAX_PAGE_SIZE


class LimitPagePagination(PageNumberPagination):
    """Вывод 6 объектов на странице."""

    page_size = MAX_PAGE_SIZE
    page_size_query_param = 'limit'
