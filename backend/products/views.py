from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
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


class MealViewSet(viewsets.ModelViewSet):
    serializer_class = MealSerializer
    permission_classes = [IsAuthenticated]
    queryset = Meal.objects.all() 
    
    @swagger_auto_schema(
        operation_description="Получить список всех приемов пищи пользователя",
        responses={
            200: MealSerializer(many=True),
            401: "Пользователь не авторизован"
        },
        tags=['Приемы пищи']
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Получить детальную информацию о приеме пищи",
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
            required=['product', 'name', 'amount'],
            properties={
                'product': openapi.Schema(type=openapi.TYPE_INTEGER, example=1, description='ID продукта'),
                'name': openapi.Schema(type=openapi.TYPE_STRING, example='Завтрак', description='Название приема пищи'),
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
            required=['product', 'name', 'amount'],
            properties={
                'product': openapi.Schema(type=openapi.TYPE_INTEGER, example=2, description='ID продукта'),
                'name': openapi.Schema(type=openapi.TYPE_STRING, example='Обед', description='Название приема пищи'),
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
                'name': openapi.Schema(type=openapi.TYPE_STRING, example='Ужин', description='Название приема пищи (необязательно)'),
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
        return self.queryset.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(user=self.request.user)