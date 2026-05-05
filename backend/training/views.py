from django.db.models import Q
from django.utils.dateparse import parse_date
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DayCompletion, Exercise, MuscleGroup, TemplateAssignment, TemplateKind, WorkoutTemplate
from .openapi_schemas import (
    DAY_PLAN_DATE_QUERY,
    EXERCISE_LIST_QUERY_PARAMS,
    PLANS_LIST_QUERY_PARAMS,
    SETS_LIST_QUERY_PARAMS,
    day_plan_completed_request_schema,
    day_workout_plan_schema,
    template_assignment_request_schema,
)
from .serializers import (
    DayPlanCompletedSerializer,
    ExerciseSerializer,
    ExerciseWriteSerializer,
    TemplateAssignmentSerializer,
    WorkoutTemplateSerializer,
)
from .services import assignments_for_day, day_completed_flag, utc_today

_SWAGGER_TAG = ['Тренировки']

_AUTH_ERROR = 'Требуется аутентификация (JWT Bearer)'


def _parse_day_param(request):
    raw = request.query_params.get('date')
    if not raw:
        return None, Response({'detail': 'Параметр date обязателен (YYYY-MM-DD)'}, status=400)
    d = parse_date(raw)
    if d is None:
        return None, Response({'detail': 'Некорректный формат date'}, status=400)
    return d, None


class PlanViewSet(viewsets.ModelViewSet):
    serializer_class = WorkoutTemplateSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = WorkoutTemplate.objects.filter(user=self.request.user, kind=TemplateKind.PLAN)
        q = self.request.query_params.get('query', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['template_kind'] = TemplateKind.PLAN
        return ctx

    @swagger_auto_schema(
        operation_summary='Список планов тренировок',
        operation_description=(
            'Шаблоны типа «план» текущего пользователя. '
            'Необязательный query — фильтр по подстроке в названии.'
        ),
        manual_parameters=PLANS_LIST_QUERY_PARAMS,
        responses={
            200: WorkoutTemplateSerializer(many=True),
            401: _AUTH_ERROR,
        },
        tags=_SWAGGER_TAG,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='План по ID',
        responses={
            200: WorkoutTemplateSerializer(),
            401: _AUTH_ERROR,
            404: 'Не найден',
        },
        tags=_SWAGGER_TAG,
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Создать план',
        operation_description='Тело без поля id; ответ — созданный WorkoutTemplate с id.',
        request_body=WorkoutTemplateSerializer,
        responses={
            201: WorkoutTemplateSerializer(),
            400: 'Ошибка валидации (структура nodes, ссылки на упражнения)',
            401: _AUTH_ERROR,
        },
        tags=_SWAGGER_TAG,
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Обновить план',
        request_body=WorkoutTemplateSerializer,
        responses={
            200: WorkoutTemplateSerializer(),
            400: 'Ошибка валидации',
            401: _AUTH_ERROR,
            404: 'Не найден',
        },
        tags=_SWAGGER_TAG,
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Удалить план',
        responses={
            204: 'Удалено',
            401: _AUTH_ERROR,
            404: 'Не найден',
        },
        tags=_SWAGGER_TAG,
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class SetViewSet(viewsets.ModelViewSet):
    serializer_class = WorkoutTemplateSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = WorkoutTemplate.objects.filter(user=self.request.user, kind=TemplateKind.SET)
        q = self.request.query_params.get('query', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        mg = self.request.query_params.get('muscleGroup', '').strip()
        if mg:
            if mg not in {c.value for c in MuscleGroup}:
                return qs.none()
            qs = qs.filter(muscle_groups__overlap=[mg])
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['template_kind'] = TemplateKind.SET
        return ctx

    @swagger_auto_schema(
        operation_summary='Список сетов (шаблонов)',
        operation_description=(
            'Та же модель, что и планы (WorkoutTemplate), kind=set. '
            'Дополнительно: фильтр muscleGroup по группам мышц в узлах.'
        ),
        manual_parameters=SETS_LIST_QUERY_PARAMS,
        responses={
            200: WorkoutTemplateSerializer(many=True),
            401: _AUTH_ERROR,
        },
        tags=_SWAGGER_TAG,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Сет по ID',
        responses={
            200: WorkoutTemplateSerializer(),
            401: _AUTH_ERROR,
            404: 'Не найден',
        },
        tags=_SWAGGER_TAG,
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Создать сет',
        request_body=WorkoutTemplateSerializer,
        responses={
            201: WorkoutTemplateSerializer(),
            400: 'Ошибка валидации',
            401: _AUTH_ERROR,
        },
        tags=_SWAGGER_TAG,
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Обновить сет',
        request_body=WorkoutTemplateSerializer,
        responses={
            200: WorkoutTemplateSerializer(),
            400: 'Ошибка валидации',
            401: _AUTH_ERROR,
            404: 'Не найден',
        },
        tags=_SWAGGER_TAG,
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Удалить сет',
        responses={
            204: 'Удалено',
            401: _AUTH_ERROR,
            404: 'Не найден',
        },
        tags=_SWAGGER_TAG,
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


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


class AssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = TemplateAssignmentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options']

    def get_queryset(self):
        return TemplateAssignment.objects.filter(user=self.request.user).select_related('template')

    @swagger_auto_schema(
        operation_summary='Список назначений шаблонов',
        responses={
            200: TemplateAssignmentSerializer(many=True),
            401: _AUTH_ERROR,
        },
        tags=_SWAGGER_TAG,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Назначение по ID',
        responses={
            200: TemplateAssignmentSerializer(),
            401: _AUTH_ERROR,
            404: 'Не найден',
        },
        tags=_SWAGGER_TAG,
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Создать назначение',
        operation_description='Привязка шаблона к календарю (anchorDate, intervalDays, …).',
        request_body=template_assignment_request_schema(),
        responses={
            201: TemplateAssignmentSerializer(),
            400: 'Ошибка валидации',
            401: _AUTH_ERROR,
        },
        tags=_SWAGGER_TAG,
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Обновить назначение',
        request_body=template_assignment_request_schema(),
        responses={
            200: TemplateAssignmentSerializer(),
            400: 'Ошибка валидации',
            401: _AUTH_ERROR,
            404: 'Не найден',
        },
        tags=_SWAGGER_TAG,
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Удалить назначение',
        responses={
            204: 'Удалено',
            401: _AUTH_ERROR,
            404: 'Не найден',
        },
        tags=_SWAGGER_TAG,
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Активные назначения',
        operation_description=(
            'Только назначения, у которых endDate отсутствует или не раньше текущей даты (UTC).'
        ),
        responses={
            200: TemplateAssignmentSerializer(many=True),
            401: _AUTH_ERROR,
        },
        tags=_SWAGGER_TAG,
    )
    @action(detail=False, methods=['get'], url_path='active')
    def active(self, request):
        today = utc_today()
        qs = self.get_queryset().filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class DayPlanView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary='План тренировок на день',
        operation_description=(
            'Собирает секции из назначений, попадающих на указанную дату по правилам anchorDate / intervalDays.'
        ),
        manual_parameters=[DAY_PLAN_DATE_QUERY],
        responses={
            200: day_workout_plan_schema(),
            400: 'Отсутствует или неверный параметр date',
            401: _AUTH_ERROR,
        },
        tags=_SWAGGER_TAG,
    )
    def get(self, request):
        d, err = _parse_day_param(request)
        if err:
            return err
        user = request.user
        matched = assignments_for_day(user, d)
        matched.sort(key=lambda a: (a.sort_order, a.anchor_date))
        sections = []
        for a in matched:
            tpl = a.template
            sections.append(
                {
                    'assignmentId': str(a.id),
                    'templateId': str(tpl.id),
                    'templateName': tpl.name,
                    'sortOrder': a.sort_order,
                    'nodes': tpl.nodes,
                }
            )
        payload = {
            'date': d.isoformat(),
            'sections': sections,
            'dayCompleted': day_completed_flag(user, d),
        }
        return Response(payload)


class DayPlanCompletedPatchView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary='Отметить день выполненным / снять отметку',
        manual_parameters=[
            openapi.Parameter(
                'date_iso',
                openapi.IN_PATH,
                description='Дата YYYY-MM-DD',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        request_body=day_plan_completed_request_schema(),
        responses={
            204: 'Нет содержимого',
            400: 'Неверный формат даты в пути или тело запроса',
            401: _AUTH_ERROR,
        },
        tags=_SWAGGER_TAG,
    )
    def patch(self, request, date_iso):
        d = parse_date(date_iso)
        if d is None:
            return Response({'detail': 'Некорректный формат даты в пути'}, status=400)
        ser = DayPlanCompletedSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        completed = ser.validated_data['completed']
        DayCompletion.objects.update_or_create(
            user=request.user,
            date=d,
            defaults={'completed': completed},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
