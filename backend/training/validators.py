from .models import Muscle, MuscleGroup


_MUSCLE_VALUES = {m.value for m in Muscle}
_MUSCLE_GROUP_VALUES = {m.value for m in MuscleGroup}


class SchemaValidationError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def _require(cond, msg):
    if not cond:
        raise SchemaValidationError(msg)


def validate_approach(obj):
    _require(isinstance(obj, dict), 'approach должен быть объектом')
    weight = obj.get('weight')
    if weight is not None:
        _require(isinstance(weight, (int, float)), 'approach.weight должен быть числом или null')
    _require('reps' in obj, 'approach.reps обязателен')
    _require(isinstance(obj['reps'], int) and not isinstance(obj['reps'], bool), 'approach.reps — целое')
    _require('setsCount' in obj, 'approach.setsCount обязателен')
    _require(
        isinstance(obj['setsCount'], int) and not isinstance(obj['setsCount'], bool),
        'approach.setsCount — целое',
    )


def validate_exercise_payload(data, require_id=False):
    _require(isinstance(data, dict), 'тело должно быть объектом')
    if require_id:
        _require('id' in data and isinstance(data['id'], str), 'id — строка')
    else:
        _require('id' not in data or data.get('id') is None, 'не передавайте id при создании')
    _require(isinstance(data.get('name'), str) and data['name'].strip(), 'name обязателен')
    desc = data.get('description')
    if desc is not None:
        _require(isinstance(desc, str), 'description — строка или null')
    mm = data.get('mainMuscles')
    _require(isinstance(mm, list), 'mainMuscles — массив строк')
    for m in mm:
        _require(m in _MUSCLE_VALUES, f'недопустимое значение Muscle: {m}')
    mg = data.get('muscleGroup')
    _require(mg in _MUSCLE_GROUP_VALUES, 'muscleGroup должен быть значением MuscleGroup')
    appr = data.get('approaches')
    _require(isinstance(appr, list), 'approaches — массив')
    for a in appr:
        validate_approach(a)
