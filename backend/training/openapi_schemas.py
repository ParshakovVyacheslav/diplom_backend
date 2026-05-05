"""Переиспользуемые OpenAPI-схемы для Swagger (drf-yasg), домен тренировок."""

from drf_yasg import openapi


def muscle_group_enum_description():
    return (
        'Значение MuscleGroup: Chest, Back, Shoulders, Biceps, Triceps, '
        'Legs, Core, Glutes, Calves, FullBody'
    )


def muscle_enum_description():
    return (
        'Значение Muscle: PectoralisMajor, LatissimusDorsi, Trapezius, Rhomboids, '
        'DeltoidAnterior, DeltoidLateral, DeltoidPosterior, BicepsBrachii, '
        'TricepsLongHead, Brachialis, Quadriceps, Hamstrings, GluteusMaximus, '
        'Gastrocnemius, Soleus, RectusAbdominis, Obliques, ErectorSpinae, ForearmFlexors'
    )


_QUERY_PARAM = openapi.Parameter(
    'query',
    openapi.IN_QUERY,
    description='Поиск по названию (подстрока, без учёта регистра)',
    type=openapi.TYPE_STRING,
    required=False,
)

_MUSCLE_GROUP_QUERY = openapi.Parameter(
    'muscleGroup',
    openapi.IN_QUERY,
    description=muscle_group_enum_description(),
    type=openapi.TYPE_STRING,
    required=False,
)

_MUSCLE_QUERY = openapi.Parameter(
    'muscle',
    openapi.IN_QUERY,
    description=muscle_enum_description(),
    type=openapi.TYPE_STRING,
    required=False,
)

EXERCISE_LIST_QUERY_PARAMS = [_QUERY_PARAM, _MUSCLE_GROUP_QUERY, _MUSCLE_QUERY]

PLANS_LIST_QUERY_PARAMS = [_QUERY_PARAM]

SETS_LIST_QUERY_PARAMS = [
    _QUERY_PARAM,
    openapi.Parameter(
        'muscleGroup',
        openapi.IN_QUERY,
        description=(
            'Необязательный фильтр: шаблон содержит упражнение с этой группой мышц. '
            + muscle_group_enum_description()
        ),
        type=openapi.TYPE_STRING,
        required=False,
    ),
]

DAY_PLAN_DATE_QUERY = openapi.Parameter(
    'date',
    openapi.IN_QUERY,
    description='Дата в формате YYYY-MM-DD',
    type=openapi.TYPE_STRING,
    required=True,
)


def plan_node_schema():
    return openapi.Schema(
        type=openapi.TYPE_OBJECT,
        description=(
            'PlanNode: узел плана — type exercise или circuit; см. спецификацию '
            '(ExerciseRef, WorkoutSetLine, CircuitExercise).'
        ),
        additional_properties=True,
    )


def scheduled_workout_section_schema():
    return openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'assignmentId': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
            'templateId': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
            'templateName': openapi.Schema(type=openapi.TYPE_STRING),
            'sortOrder': openapi.Schema(type=openapi.TYPE_INTEGER),
            'nodes': openapi.Schema(type=openapi.TYPE_ARRAY, items=plan_node_schema()),
        },
        required=['assignmentId', 'templateId', 'templateName', 'sortOrder', 'nodes'],
    )


def day_workout_plan_schema():
    return openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'date': openapi.Schema(type=openapi.TYPE_STRING, description='YYYY-MM-DD'),
            'sections': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=scheduled_workout_section_schema(),
            ),
            'dayCompleted': openapi.Schema(type=openapi.TYPE_BOOLEAN),
        },
        required=['date', 'sections', 'dayCompleted'],
    )


def day_plan_completed_request_schema():
    return openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'completed': openapi.Schema(type=openapi.TYPE_BOOLEAN),
        },
        required=['completed'],
    )


def template_assignment_request_schema():
    return openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['templateId', 'anchorDate', 'intervalDays', 'sortOrder'],
        properties={
            'templateId': openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                description='ID шаблона (план или сет)',
            ),
            'anchorDate': openapi.Schema(type=openapi.TYPE_STRING, description='YYYY-MM-DD'),
            'intervalDays': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description='Интервал в днях; 0 — без повторений (только anchorDate)',
            ),
            'endDate': openapi.Schema(
                type=openapi.TYPE_STRING,
                description='YYYY-MM-DD или отсутствует; null — бессрочно',
                x_nullable=True,
            ),
            'sortOrder': openapi.Schema(type=openapi.TYPE_INTEGER),
        },
    )
