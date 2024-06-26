import io

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import status
from rest_framework.response import Response

from recipes.models import Recipe
from .constans import (FONT_HEIGHT, HORISONTAL_POSITION_TEXT_ON_PAGE,
                       HORISONTAL_POSITION_TITUL_ON_PAGE, MAX_INTERVAL_LINES,
                       MIN_VALUE, VERTICAL_POSITION_TEXT_ON_PAGE,
                       VERTICAL_POSITION_TITUL_ON_PAGE)


def create_shopping_cart(ingredients_cart):
    """Функция для формирования списка покупок для скачивания."""

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        "attachment; filename='shopping_cart.pdf'"
    )
    pdfmetrics.registerFont(
        TTFont('Arial', 'data/arial.ttf', 'UTF-8')
    )
    buffer = io.BytesIO()
    pdf_file = canvas.Canvas(buffer)
    pdf_file.setFont('Arial', FONT_HEIGHT)
    pdf_file.drawString(VERTICAL_POSITION_TITUL_ON_PAGE,
                        HORISONTAL_POSITION_TITUL_ON_PAGE,
                        'Список покупок.')
    pdf_file.setFont('Arial', FONT_HEIGHT)
    from_bottom = VERTICAL_POSITION_TEXT_ON_PAGE
    for number, ingredient in enumerate(ingredients_cart, start=MIN_VALUE):
        pdf_file.drawString(
            HORISONTAL_POSITION_TEXT_ON_PAGE,
            from_bottom,
            f"{number}. {ingredient['ingredient__name']}: "
            f"{ingredient['ingredient_value']} "
            f"{ingredient['ingredient__measurement_unit']}.",
        )
        from_bottom -= MAX_INTERVAL_LINES
        if from_bottom <= HORISONTAL_POSITION_TEXT_ON_PAGE:
            from_bottom = HORISONTAL_POSITION_TITUL_ON_PAGE
            pdf_file.showPage()
            pdf_file.setFont('Arial', FONT_HEIGHT)
    pdf_file.showPage()
    pdf_file.save()
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


def add_or_del_obj(pk, request, param, serializer_context):
    """"Функция для добавления или удаления объекта"""

    obj = get_object_or_404(Recipe, pk=pk)
    obj_bool = param.filter(pk=obj.pk).exists()
    if request.method == 'DELETE' and obj_bool:
        param.remove(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)
    if request.method == 'POST' and not obj_bool:
        param.add(obj)
        serializer = serializer_context(
            obj, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(status=status.HTTP_400_BAD_REQUEST)
