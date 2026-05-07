from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Assignment, AssignmentTemplate, Exercise
from .openapi_schemas import ASSIGNMENT_DATE_PATH_PARAM, EXERCISE_LIST_QUERY_PARAMS
from .serializers import (
    AssignmentReadSerializer,
    AssignmentTemplatePatchSerializer,
    AssignmentTemplatePutSerializer,
    AssignmentTemplateReadSerializer,
    ExerciseSerializer,
    ExerciseWriteSerializer,
    StandaloneAssignmentPutSerializer,
    prefetch_assignments_nested,
    prefetch_template_nested,
)
from .services import (
    create_scheduled_assignment_template,
    persist_workout_sets_for_template,
    replace_assignments_for_day,
    reschedule_assignments_for_template,
)

_SWAGGER_TAG = ['Тренировки']

_AUTH_ERROR = 'Требуется аутентификация (JWT Bearer)'


def _assignment_date_bad():
    return Response({'detail': 'Некорректная дата (ожидается YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)


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


class AssignmentTemplateViewSet(viewsets.ModelViewSet):
    """CRUD по шаблонам; сеты только в теле запроса, отдельных URL для сета нет."""

    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']
    lookup_field = 'pk'

    def get_queryset(self):
        return prefetch_template_nested(AssignmentTemplate.objects.filter(user=self.request.user)).order_by('name')

    def get_serializer_class(self):
        return AssignmentTemplateReadSerializer

    @swagger_auto_schema(
        operation_summary='Список шаблонов тренировок текущего пользователя',
        responses={200: AssignmentTemplateReadSerializer(many=True), 401: _AUTH_ERROR},
        tags=_SWAGGER_TAG,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Шаблон по id',
        responses={200: AssignmentTemplateReadSerializer(), 401: _AUTH_ERROR, 404: 'Не найден'},
        tags=_SWAGGER_TAG,
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Создать шаблон и назначения по календарю',
        operation_description=(
            'Создаёт AssignmentTemplate и WorkoutSet/Approach из поля sets, '
            'затем генерирует Assignment на даты согласно daysOfWeek до endDate '
            '(либо горизонт TRAINING_SCHEDULE_DEFAULT_DAYS, если endDate пустой). '
            'scheduleStartDate — дата начала генерации (по умолчанию сегодня).'
        ),
        request_body=AssignmentTemplatePutSerializer,
        responses={
            201: AssignmentTemplateReadSerializer(),
            400: 'Ошибка валидации',
            401: _AUTH_ERROR,
        },
        tags=_SWAGGER_TAG,
    )
    def create(self, request, *args, **kwargs):
        ser = AssignmentTemplatePutSerializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)
        try:
            tmpl = create_scheduled_assignment_template(request.user, ser.validated_data)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        fresh = prefetch_template_nested(AssignmentTemplate.objects.filter(pk=tmpl.pk)).first()
        out = AssignmentTemplateReadSerializer(fresh)
        return Response(out.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary='Обновить шаблон полностью (PUT)',
        request_body=AssignmentTemplatePutSerializer,
        responses={
            200: AssignmentTemplateReadSerializer(),
            400: 'Ошибка валидации',
            401: _AUTH_ERROR,
            404: 'Не найден',
        },
        tags=_SWAGGER_TAG,
    )
    def update(self, request, *args, **kwargs):
        return self._update_template(request, partial=False)

    @swagger_auto_schema(
        operation_summary='Частично обновить шаблон (PATCH)',
        request_body=AssignmentTemplatePatchSerializer,
        responses={
            200: AssignmentTemplateReadSerializer(),
            400: 'Ошибка валидации',
            401: _AUTH_ERROR,
            404: 'Не найден',
        },
        tags=_SWAGGER_TAG,
    )
    def partial_update(self, request, *args, **kwargs):
        return self._update_template(request, partial=True)

    def _update_template(self, request, *, partial):
        instance = self.get_object()
        ser_cls = AssignmentTemplatePatchSerializer if partial else AssignmentTemplatePutSerializer
        ser = ser_cls(data=request.data, partial=partial, context={'request': request})
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        orig_days = list(instance.days_of_week)
        orig_end = instance.end_date

        with transaction.atomic():
            if not partial:
                instance.name = v['name']
                instance.days_of_week = v['daysOfWeek']
                instance.end_date = v.get('endDate')
            else:
                if 'name' in v:
                    instance.name = v['name']
                if 'daysOfWeek' in v:
                    instance.days_of_week = v['daysOfWeek']
                if 'endDate' in v:
                    instance.end_date = v['endDate']
            instance.save()

            try:
                if 'sets' in v:
                    persist_workout_sets_for_template(instance, v['sets'])
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc

            schedule_changed = (list(instance.days_of_week) != orig_days) or (instance.end_date != orig_end)
            start = v.get('scheduleStartDate') or timezone.now().date()

            try:
                if schedule_changed:
                    reschedule_assignments_for_template(instance, start)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc

        fresh = prefetch_template_nested(AssignmentTemplate.objects.filter(pk=instance.pk)).first()
        return Response(AssignmentTemplateReadSerializer(fresh).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary='Удалить шаблон',
        operation_description='Каскадно удалятся связанные назначения, сеты и подходы.',
        responses={
            204: 'Удалено',
            401: _AUTH_ERROR,
            404: 'Не найден',
        },
        tags=_SWAGGER_TAG,
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class AssignmentByDateView(APIView):
    """Назначения на конкретную дату: список, массовое удаление, замена содержимого дня через новый шаблон."""

    permission_classes = [IsAuthenticated]

    def _parse_date(self, date_iso):
        d = parse_date(date_iso)
        if d is None:
            return None, _assignment_date_bad()
        return d, None

    @swagger_auto_schema(
        operation_summary='Назначения на дату',
        manual_parameters=[ASSIGNMENT_DATE_PATH_PARAM],
        responses={200: AssignmentReadSerializer(many=True), 401: _AUTH_ERROR, 400: 'Неверная дата'},
        tags=_SWAGGER_TAG,
    )
    def get(self, request, date_iso, *args, **kwargs):
        d, err = self._parse_date(date_iso)
        if err:
            return err
        qs = prefetch_assignments_nested(
            Assignment.objects.filter(user=request.user, date=d).order_by('template__name', 'id'),
        )
        return Response(AssignmentReadSerializer(qs, many=True).data)

    @swagger_auto_schema(
        operation_summary='Удалить все назначения на дату',
        manual_parameters=[ASSIGNMENT_DATE_PATH_PARAM],
        responses={204: 'Удалено', 401: _AUTH_ERROR, 400: 'Неверная дата'},
        tags=_SWAGGER_TAG,
    )
    def delete(self, request, date_iso, *args, **kwargs):
        d, err = self._parse_date(date_iso)
        if err:
            return err
        Assignment.objects.filter(user=request.user, date=d).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_summary='Заменить тренировки на дату',
        operation_description=(
            'Удаляет все назначения пользователя на эту дату, создаёт новый AssignmentTemplate '
            'с переданными сетами и одно назначение на указанную дату.'
        ),
        manual_parameters=[ASSIGNMENT_DATE_PATH_PARAM],
        request_body=StandaloneAssignmentPutSerializer,
        responses={
            200: AssignmentReadSerializer(many=True),
            400: 'Ошибка валидации',
            401: _AUTH_ERROR,
        },
        tags=_SWAGGER_TAG,
    )
    def put(self, request, date_iso, *args, **kwargs):
        d, err = self._parse_date(date_iso)
        if err:
            return err
        ser = StandaloneAssignmentPutSerializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)
        try:
            replace_assignments_for_day(request.user, d, ser.validated_data)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        qs = prefetch_assignments_nested(
            Assignment.objects.filter(user=request.user, date=d).order_by('template__name', 'id'),
        )
        return Response(AssignmentReadSerializer(qs, many=True).data, status=status.HTTP_200_OK)
