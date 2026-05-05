from .models import Exercise, Muscle, MuscleGroup


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


def validate_exercise_ref(ref, path='ref'):
    _require(isinstance(ref, dict), f'{path} должен быть объектом')
    t = ref.get('type')
    _require(t in ('global', 'personal'), f'{path}.type должен быть "global" или "personal"')
    _require('exerciseId' in ref and isinstance(ref['exerciseId'], str), f'{path}.exerciseId — строка')


def validate_workout_set_line(sl, path='setLines'):
    _require(isinstance(sl, dict), f'{path} элемент должен быть объектом')
    for key in ('weightKg', 'reps', 'sets'):
        _require(key in sl, f'{path}.{key} обязателен')
    _require(isinstance(sl['weightKg'], (int, float)), f'{path}.weightKg — число')
    _require(isinstance(sl['reps'], int) and not isinstance(sl['reps'], bool), f'{path}.reps — целое')
    _require(isinstance(sl['sets'], int) and not isinstance(sl['sets'], bool), f'{path}.sets — целое')


def validate_plan_nodes(nodes):
    _require(isinstance(nodes, list), 'nodes должен быть массивом')
    for i, node in enumerate(nodes):
        _require(isinstance(node, dict), f'nodes[{i}] должен быть объектом')
        nt = node.get('type')
        _require(nt in ('exercise', 'circuit'), f'nodes[{i}].type должен быть "exercise" или "circuit"')
        if nt == 'exercise':
            validate_exercise_ref(node.get('ref'), path=f'nodes[{i}].ref')
            sl = node.get('setLines')
            _require(isinstance(sl, list), f'nodes[{i}].setLines — массив')
            for j, line in enumerate(sl):
                validate_workout_set_line(line, path=f'nodes[{i}].setLines[{j}]')
            _require('usesAddedWeight' in node, f'nodes[{i}].usesAddedWeight обязателен')
            _require(isinstance(node['usesAddedWeight'], bool), f'nodes[{i}].usesAddedWeight — boolean')
        else:
            title = node.get('title')
            if title is not None:
                _require(isinstance(title, str), f'nodes[{i}].title — строка или null')
            _require('rounds' in node, f'nodes[{i}].rounds обязателен')
            _require(
                isinstance(node['rounds'], int) and not isinstance(node['rounds'], bool),
                f'nodes[{i}].rounds — целое',
            )
            exs = node.get('exercises')
            _require(isinstance(exs, list), f'nodes[{i}].exercises — массив')
            for j, ce in enumerate(exs):
                _require(isinstance(ce, dict), f'nodes[{i}].exercises[{j}] — объект')
                validate_exercise_ref(ce.get('ref'), path=f'nodes[{i}].exercises[{j}].ref')
                sl = ce.get('setLines')
                _require(isinstance(sl, list), f'nodes[{i}].exercises[{j}].setLines — массив')
                for k, line in enumerate(sl):
                    validate_workout_set_line(
                        line,
                        path=f'nodes[{i}].exercises[{j}].setLines[{k}]',
                    )
                _require(
                    'usesAddedWeight' in ce,
                    f'nodes[{i}].exercises[{j}].usesAddedWeight обязателен',
                )
                _require(
                    isinstance(ce['usesAddedWeight'], bool),
                    f'nodes[{i}].exercises[{j}].usesAddedWeight — boolean',
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


def collect_muscle_groups_for_nodes(user, nodes):
    groups = []
    seen = set()

    def add_group(val):
        if val not in seen:
            seen.add(val)
            groups.append(val)

    def resolve_ref(ref):
        validate_exercise_ref(ref)
        ex_id = ref['exerciseId']
        if ref['type'] == 'global':
            ex = Exercise.objects.filter(user__isnull=True, id=ex_id).first()
        else:
            ex = Exercise.objects.filter(user=user, id=ex_id).first()
        _require(ex is not None, f'Упражнение не найдено: {ref["type"]} / {ex_id}')
        add_group(ex.muscle_group)

    def walk(node_list):
        for node in node_list:
            nt = node.get('type')
            if nt == 'exercise':
                resolve_ref(node['ref'])
            elif nt == 'circuit':
                for ce in node['exercises']:
                    resolve_ref(ce['ref'])

    walk(nodes)
    return groups


def ids_exist_for_nodes(user, nodes):
    validate_plan_nodes(nodes)

    def check_ref(ref):
        ex_id = ref['exerciseId']
        if ref['type'] == 'global':
            exists = Exercise.objects.filter(user__isnull=True, id=ex_id).exists()
        else:
            exists = Exercise.objects.filter(user=user, id=ex_id).exists()
        _require(exists, f'Упражнение не найдено: {ref["type"]} / {ex_id}')

    for node in nodes:
        if node['type'] == 'exercise':
            check_ref(node['ref'])
        else:
            for ce in node['exercises']:
                check_ref(ce['ref'])
