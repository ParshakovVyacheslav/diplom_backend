import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db.models import F
from django.contrib.postgres.search import TrigramSimilarity
from rest_framework import viewsets, mixins, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Product, Meal
from .serializers import ProductSerializer, MealSerializer


class ProductViewSet(mixins.RetrieveModelMixin,
                     mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    search_similarity_threshold = 0.1

    @swagger_auto_schema(
        operation_description="Получить список всех продуктов",
        responses={
            200: ProductSerializer(many=True),
            401: "Пользователь не авторизован"
        },
        tags=['Продукты']
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Получить детальную информацию о продукте",
        responses={
            200: ProductSerializer(),
            401: "Пользователь не авторизован",
            404: "Продукт не найден"
        },
        tags=['Продукты']
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Поиск продуктов по названию (триграммный поиск)",
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description='Строка поиска',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description='Количество результатов (по умолчанию 10)',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'name': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Параметр q обязателен",
            401: "Пользователь не авторизован"
        },
        tags=['Продукты']
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request, *args, **kwargs):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response(
                {'detail': 'Параметр q обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            limit = int(request.query_params.get('limit', 10))
        except (TypeError, ValueError):
            limit = 10

        limit = max(1, limit)

        products = (
            Product.objects
            .annotate(similarity=TrigramSimilarity('name', query))
            .filter(similarity__gte=self.search_similarity_threshold)
            .order_by(F('similarity').desc(), 'id')
            .values('id', 'name')[:limit]
        )

        return Response(list(products), status=status.HTTP_200_OK)


class MealViewSet(viewsets.ModelViewSet):
    serializer_class = MealSerializer
    permission_classes = [IsAuthenticated]
    queryset = Meal.objects.all() 
    
    @swagger_auto_schema(
        operation_description=(
            "Получить список приемов пищи пользователя. "
            "В элементе списка поле name содержит название связанного продукта (Product.name). "
            "Необязательный параметр date (календарная дата ISO 8601, YYYY-MM-DD) ограничивает выборку "
            "приемами пищи за этот локальный календарный день. Часовой пояс задаётся параметром timezone "
            "(IANA, например Europe/Moscow); если не указан — используется UTC."
        ),
        manual_parameters=[
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description=(
                    'Дата в формате ISO 8601 (YYYY-MM-DD). '
                    'Возвращаются только приёмы пищи за этот календарный день в выбранном часовом поясе.'
                ),
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                required=False,
            ),
            openapi.Parameter(
                'timezone',
                openapi.IN_QUERY,
                description=(
                    'Идентификатор часового пояса IANA (например Europe/Moscow, America/New_York). '
                    'По умолчанию UTC.'
                ),
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
        responses={
            200: MealSerializer(many=True),
            400: "Некорректные параметры date или timezone",
            401: "Пользователь не авторизован"
        },
        tags=['Приемы пищи']
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description=(
            "Получить детальную информацию о приеме пищи; "
            "поле name в ответе — название связанного продукта."
        ),
        responses={
            200: MealSerializer(),
            401: "Пользователь не авторизован",
            404: "Прием пищи не найден"
        },
        tags=['Приемы пищи']
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Создать новый прием пищи",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['product', 'type', 'amount'],
            properties={
                'product': openapi.Schema(type=openapi.TYPE_INTEGER, example=1, description='ID продукта'),
                'type': openapi.Schema(type=openapi.TYPE_STRING, example='Завтрак', description='Название приема пищи'),
                'amount': openapi.Schema(type=openapi.TYPE_INTEGER, example=150, description='Количество в граммах'),
                'position': openapi.Schema(type=openapi.TYPE_INTEGER, example=1, description='Порядковый номер')
            }
        ),
        responses={
            201: MealSerializer(),
            400: "Неверные данные",
            401: "Пользователь не авторизован"
        },
        tags=['Приемы пищи']
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Обновить прием пищи",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['product', 'type', 'amount'],
            properties={
                'product': openapi.Schema(type=openapi.TYPE_INTEGER, example=2, description='ID продукта'),
                'type': openapi.Schema(type=openapi.TYPE_STRING, example='Обед', description='Название приема пищи'),
                'amount': openapi.Schema(type=openapi.TYPE_INTEGER, example=200, description='Количество в граммах'),
                'position': openapi.Schema(type=openapi.TYPE_INTEGER, example=2, description='Порядковый номер')
            }
        ),
        responses={
            200: MealSerializer(),
            400: "Неверные данные",
            401: "Пользователь не авторизован",
            404: "Прием пищи не найден"
        },
        tags=['Приемы пищи']
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Частично обновить прием пищи",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'product': openapi.Schema(type=openapi.TYPE_INTEGER, example=3, description='ID продукта (необязательно)'),
                'type': openapi.Schema(type=openapi.TYPE_STRING, example='Ужин', description='Название приема пищи (необязательно)'),
                'amount': openapi.Schema(type=openapi.TYPE_INTEGER, example=180, description='Количество в граммах (необязательно)'),
                'position': openapi.Schema(type=openapi.TYPE_INTEGER, example=3, description='Порядковый номер (необязательно)')
            }
        ),
        responses={
            200: MealSerializer(),
            400: "Неверные данные",
            401: "Пользователь не авторизован",
            404: "Прием пищи не найден"
        },
        tags=['Приемы пищи']
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Удалить прием пищи",
        responses={
            204: "Прием пищи удален",
            401: "Пользователь не авторизован",
            404: "Прием пищи не найден"
        },
        tags=['Приемы пищи']
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        qs = self.queryset.filter(user=self.request.user).select_related('product')
        if self.action != 'list':
            return qs

        raw = self.request.query_params.get('date')
        if raw is None or raw == '':
            return qs

        raw = raw.strip()
        try:
            day = datetime.date.fromisoformat(raw)
        except ValueError:
            raise ValidationError(
                {'date': 'Ожидается дата в формате ISO 8601 (YYYY-MM-DD).'}
            )

        tz_name = (self.request.query_params.get('timezone') or 'UTC').strip()
        if not tz_name:
            tz_name = 'UTC'
        try:
            tz = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            raise ValidationError(
                {
                    'timezone': 'Неизвестный часовой пояс. Укажите имя IANA, например Europe/Moscow.'
                }
            )

        start_local = datetime.datetime.combine(
            day, datetime.time.min, tzinfo=tz
        )
        end_local = start_local + datetime.timedelta(days=1)
        return qs.filter(date__gte=start_local, date__lt=end_local)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(user=self.request.user)