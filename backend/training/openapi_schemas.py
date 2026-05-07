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
