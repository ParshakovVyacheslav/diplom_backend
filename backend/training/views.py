from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Approach,
    Assignment,
    AssignmentApproachProgress,
    AssignmentTemplate,
    AssignmentWorkoutSetProgress,
    Exercise,
    WorkoutSet,
)
from .openapi_schemas import (
    ASSIGNMENT_APPROACH_PATH_PARAMS,
    ASSIGNMENT_DATE_PATH_PARAM,
    ASSIGNMENT_WORKOUT_SET_PATH_PARAMS,
    EXERCISE_LIST_QUERY_PARAMS,
)
from .serializers import (
    ApproachIsDonePatchSerializer,
    ApproachNestedReadSerializer,
    AssignmentIsDonePatchSerializer,
    AssignmentReadSerializer,
    AssignmentTemplatePatchSerializer,
    AssignmentTemplatePutSerializer,
    AssignmentTemplateReadSerializer,
    ExerciseSerializer,
    ExerciseWriteSerializer,
    StandaloneAssignmentPutSerializer,
    WorkoutSetReadSerializer,
    WorkoutSetRoundsRemainsPatchSerializer,
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
            'затем при isActive=true (по умолчанию) генерирует Assignment на даты согласно daysOfWeek до endDate '
            '(либо горизонт TRAINING_SCHEDULE_DEFAULT_DAYS, если endDate пустой). '
            'При isActive=false назначения не создаются. '
            'В каждом элементе sets: rounds (≥1, по умолчанию 1) — плановое число «кругов» сета; '
            'остаток по каждому назначению клиент видит как roundsRemains. '
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
        operation_description=(
            'Полная замена полей шаблона и сетов. Поле isActive необязательно: '
            'если не передано, флаг активности не меняется.'
        ),
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
        operation_description=(
            'Можно передать isActive: false — все Assignment по шаблону удаляются; '
            'isActive: true — назначения пересобираются с scheduleStartDate (или с сегодня).'
        ),
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
        orig_is_active = instance.is_active

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
            if 'isActive' in v:
                instance.is_active = v['isActive']
            instance.save()

            try:
                if 'sets' in v:
                    persist_workout_sets_for_template(instance, v['sets'])
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc

            schedule_changed = (list(instance.days_of_week) != orig_days) or (instance.end_date != orig_end)
            is_active_changed = instance.is_active != orig_is_active
            start = v.get('scheduleStartDate') or timezone.now().date()

            try:
                if schedule_changed or is_active_changed:
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


class AssignmentIsDonePatchView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary='Отметить назначение выполненным / невыполненным',
        request_body=AssignmentIsDonePatchSerializer,
        responses={200: AssignmentReadSerializer(), 400: 'Ошибка валидации', 401: _AUTH_ERROR, 404: 'Не найдено'},
        tags=_SWAGGER_TAG,
    )
    def patch(self, request, pk, *args, **kwargs):
        qs = prefetch_assignments_nested(Assignment.objects.filter(user=request.user))
        assignment = get_object_or_404(qs, pk=pk)
        ser = AssignmentIsDonePatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        assignment.is_done = ser.validated_data['isDone']
        assignment.save(update_fields=['is_done'])
        fresh = prefetch_assignments_nested(Assignment.objects.filter(pk=assignment.pk)).first()
        return Response(AssignmentReadSerializer(fresh).data, status=status.HTTP_200_OK)


class ApproachIsDonePatchView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary='Отметить подход выполненным по конкретному назначению',
        operation_description=(
            'Подход (approach) задаётся шаблоном; прогресс хранится для пары (назначение, подход). '
            'Тот же шаблон у других назначений не затрагивается.'
        ),
        manual_parameters=ASSIGNMENT_APPROACH_PATH_PARAMS,
        request_body=ApproachIsDonePatchSerializer,
        responses={
            200: ApproachNestedReadSerializer(),
            400: 'Ошибка валидации',
            401: _AUTH_ERROR,
            404: 'Не найдено',
        },
        tags=_SWAGGER_TAG,
    )
    def patch(self, request, assignment_pk, approach_pk, *args, **kwargs):
        assignment = get_object_or_404(
            prefetch_assignments_nested(Assignment.objects.filter(user=request.user)),
            pk=assignment_pk,
        )
        approach = get_object_or_404(
            Approach.objects.select_related('exercise', 'workout_set__template'),
            pk=approach_pk,
            workout_set__template__user=request.user,
        )
        if approach.workout_set.template_id != assignment.template_id:
            raise ValidationError('Подход не принадлежит шаблону этого назначения')
        ser = ApproachIsDonePatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        AssignmentApproachProgress.objects.update_or_create(
            assignment=assignment,
            approach=approach,
            defaults={'is_done': ser.validated_data['isDone']},
        )
        done_map = dict(
            AssignmentApproachProgress.objects.filter(assignment=assignment).values_list(
                'approach_id',
                'is_done',
            ),
        )
        ctx = {'approach_done': done_map}
        return Response(
            ApproachNestedReadSerializer(approach, context=ctx).data,
            status=status.HTTP_200_OK,
        )


class WorkoutSetRoundsRemainsPatchView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary='Остаток кругов сета по конкретному назначению',
        operation_description=(
            'Обновляет roundsRemains для пары (назначение, сет). Допустимо 0 … workoutSet.rounds '
            '(поле rounds из шаблонного сета в ответе по дате).'
        ),
        manual_parameters=ASSIGNMENT_WORKOUT_SET_PATH_PARAMS,
        request_body=WorkoutSetRoundsRemainsPatchSerializer,
        responses={
            200: WorkoutSetReadSerializer(),
            400: 'Ошибка валидации',
            401: _AUTH_ERROR,
            404: 'Не найдено',
        },
        tags=_SWAGGER_TAG,
    )
    def patch(self, request, assignment_pk, workout_set_pk, *args, **kwargs):
        assignment = get_object_or_404(
            prefetch_assignments_nested(Assignment.objects.filter(user=request.user)),
            pk=assignment_pk,
        )
        ws = get_object_or_404(
            WorkoutSet.objects.select_related('template'),
            pk=workout_set_pk,
            template__user=request.user,
        )
        if ws.template_id != assignment.template_id:
            raise ValidationError('Сет не принадлежит шаблону этого назначения')
        ser = WorkoutSetRoundsRemainsPatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = int(ser.validated_data['roundsRemains'])
        if v > ws.rounds:
            raise ValidationError(f'roundsRemains не больше запланированных кругов ({ws.rounds}).')
        AssignmentWorkoutSetProgress.objects.update_or_create(
            assignment=assignment,
            workout_set=ws,
            defaults={'rounds_remains': v},
        )
        rm = dict(
            AssignmentWorkoutSetProgress.objects.filter(assignment=assignment).values_list(
                'workout_set_id',
                'rounds_remains',
            ),
        )
        return Response(
            WorkoutSetReadSerializer(
                ws,
                context={'request': request, 'set_rounds_remains': rm},
            ).data,
            status=status.HTTP_200_OK,
        )
