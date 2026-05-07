from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Exercise
from .openapi_schemas import EXERCISE_LIST_QUERY_PARAMS
from .serializers import ExerciseSerializer, ExerciseWriteSerializer

_SWAGGER_TAG = ['Тренировки']

_AUTH_ERROR = 'Требуется аутентификация (JWT Bearer)'


class ExerciseGlobalListView(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ExerciseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Exercise.objects.filter(user__isnull=True)
        q = self.request.query_params.get('query', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        mg = self.request.query_params.get('muscleGroup', '').strip()
        if mg:
            qs = qs.filter(muscle_group=mg)
        muscle = self.request.query_params.get('muscle', '').strip()
        if muscle:
            qs = qs.filter(main_muscles__contains=muscle)
        return qs.order_by('name')

    @swagger_auto_schema(
        operation_summary='Глобальный каталог упражнений',
        operation_description='Упражнения без привязки к пользователю (user is null).',
        manual_parameters=EXERCISE_LIST_QUERY_PARAMS,
        responses={
            200: ExerciseSerializer(many=True),
            401: _AUTH_ERROR,
        },
        tags=_SWAGGER_TAG,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ExercisePersonalListCreateView(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ExerciseSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return ExerciseWriteSerializer
        return ExerciseSerializer

    def get_queryset(self):
        qs = Exercise.objects.filter(user=self.request.user)
        q = self.request.query_params.get('query', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        mg = self.request.query_params.get('muscleGroup', '').strip()
        if mg:
            qs = qs.filter(muscle_group=mg)
        muscle = self.request.query_params.get('muscle', '').strip()
        if muscle:
            qs = qs.filter(main_muscles__contains=muscle)
        return qs.order_by('name')

    @swagger_auto_schema(
        operation_summary='Личные упражнения',
        manual_parameters=EXERCISE_LIST_QUERY_PARAMS,
        responses={
            200: ExerciseSerializer(many=True),
            401: _AUTH_ERROR,
        },
        tags=_SWAGGER_TAG,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Создать личное упражнение',
        operation_description='Тело без id; ответ — Exercise с присвоенным id.',
        request_body=ExerciseWriteSerializer,
        responses={
            201: ExerciseSerializer(),
            400: 'Ошибка валидации полей / подходов',
            401: _AUTH_ERROR,
        },
        tags=_SWAGGER_TAG,
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
