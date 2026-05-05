"""Заполнение БД глобальными упражнениями (Exercise с user=NULL).

Пример локально:
    python manage.py seed_global_exercises
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from training.models import Exercise, Muscle, MuscleGroup


def _ap(weight, reps, sets_count):
    return {'weight': weight, 'reps': reps, 'setsCount': sets_count}


# Эталонные записи (≥50); имена уникальны среди глобальных для корректного get/update.
GLOBAL_EXERCISES_SEED = [
    # Грудь
    {'name': 'Жим штанги лёжа', 'description': 'Классический жим на горизонтальной скамье.', 'main_muscles': [Muscle.PECTORALIS_MAJOR.value, Muscle.TRICEPS_LONG_HEAD.value], 'muscle_group': MuscleGroup.CHEST.value, 'approaches': [_ap(None, 10, 3)]},
    {'name': 'Жим гантелей лёжа', 'description': 'Большая амплитуда, чем со штангой.', 'main_muscles': [Muscle.PECTORALIS_MAJOR.value, Muscle.DELTOID_ANTERIOR.value], 'muscle_group': MuscleGroup.CHEST.value, 'approaches': [_ap(None, 12, 3)]},
    {'name': 'Жим на наклонной скамье 30°', 'description': 'Акцент на верхнюю часть груди.', 'main_muscles': [Muscle.PECTORALIS_MAJOR.value, Muscle.DELTOID_ANTERIOR.value], 'muscle_group': MuscleGroup.CHEST.value, 'approaches': [_ap(None, 10, 4)]},
    {'name': 'Разводка гантелей лёжа', 'description': 'Изоляция грудных.', 'main_muscles': [Muscle.PECTORALIS_MAJOR.value], 'muscle_group': MuscleGroup.CHEST.value, 'approaches': [_ap(None, 15, 3)]},
    {'name': 'Отжимания от пола', 'description': 'Собственный вес.', 'main_muscles': [Muscle.PECTORALIS_MAJOR.value, Muscle.TRICEPS_LONG_HEAD.value], 'muscle_group': MuscleGroup.CHEST.value, 'approaches': [_ap(None, 15, 3)]},
    {'name': 'Сведения в кроссовере', 'description': 'Концентрическое сокращение груди.', 'main_muscles': [Muscle.PECTORALIS_MAJOR.value], 'muscle_group': MuscleGroup.CHEST.value, 'approaches': [_ap(None, 12, 4)]},
    {'name': 'Пуловер с гантелью', 'description': 'Растяжение грудной клетки и спины.', 'main_muscles': [Muscle.PECTORALIS_MAJOR.value, Muscle.LATISSIMUS_DORSI.value], 'muscle_group': MuscleGroup.CHEST.value, 'approaches': [_ap(None, 12, 3)]},
    {'name': 'Жим в тренажёре Смита', 'description': 'Фиксированная траектория.', 'main_muscles': [Muscle.PECTORALIS_MAJOR.value, Muscle.TRICEPS_LONG_HEAD.value], 'muscle_group': MuscleGroup.CHEST.value, 'approaches': [_ap(None, 8, 4)]},
    # Спина
    {'name': 'Подтягивания широким хватом', 'description': 'Верх спины.', 'main_muscles': [Muscle.LATISSIMUS_DORSI.value, Muscle.BICEPS_BRACHII.value], 'muscle_group': MuscleGroup.BACK.value, 'approaches': [_ap(None, 8, 4)]},
    {'name': 'Тяга верхнего блока к груди', 'description': 'Альтернатива подтягиваниям.', 'main_muscles': [Muscle.LATISSIMUS_DORSI.value, Muscle.BICEPS_BRACHII.value], 'muscle_group': MuscleGroup.BACK.value, 'approaches': [_ap(None, 12, 3)]},
    {'name': 'Тяга штанги в наклоне', 'description': 'Прокачка средней спины.', 'main_muscles': [Muscle.RHOMBOIDS.value, Muscle.LATISSIMUS_DORSI.value], 'muscle_group': MuscleGroup.BACK.value, 'approaches': [_ap(None, 10, 4)]},
    {'name': 'Тяга гантели одной рукой в упоре', 'description': 'Улучшение симметрии.', 'main_muscles': [Muscle.LATISSIMUS_DORSI.value, Muscle.RHOMBOIDS.value], 'muscle_group': MuscleGroup.BACK.value, 'approaches': [_ap(None, 12, 3)]},
    {'name': 'Гиперэкстензия', 'description': 'Разгибатели позвоночника.', 'main_muscles': [Muscle.ERECTOR_SPINAE.value, Muscle.GLUTEUS_MAXIMUS.value], 'muscle_group': MuscleGroup.BACK.value, 'approaches': [_ap(None, 15, 3)]},
    {'name': 'Шраги со штангой', 'description': 'Трапеции.', 'main_muscles': [Muscle.TRAPEZIUS.value], 'muscle_group': MuscleGroup.BACK.value, 'approaches': [_ap(None, 12, 4)]},
    {'name': 'Тяга Т-грифта', 'description': 'Толщина спины.', 'main_muscles': [Muscle.LATISSIMUS_DORSI.value, Muscle.RHOMBOIDS.value], 'muscle_group': MuscleGroup.BACK.value, 'approaches': [_ap(None, 10, 3)]},
    {'name': 'Обратные разводки на заднюю дельту', 'description': 'Задний пучок и ромбовидные.', 'main_muscles': [Muscle.DELTOID_POSTERIOR.value, Muscle.RHOMBOIDS.value], 'muscle_group': MuscleGroup.BACK.value, 'approaches': [_ap(None, 15, 3)]},
    {'name': 'Тяга нижнего блока сидя', 'description': 'Нейтральный хват.', 'main_muscles': [Muscle.LATISSIMUS_DORSI.value], 'muscle_group': MuscleGroup.BACK.value, 'approaches': [_ap(None, 12, 4)]},
    # Плечи
    {'name': 'Жим штанги стоя (армейский)', 'description': 'Фронтальная дельта.', 'main_muscles': [Muscle.DELTOID_ANTERIOR.value, Muscle.TRICEPS_LONG_HEAD.value], 'muscle_group': MuscleGroup.SHOULDERS.value, 'approaches': [_ap(None, 8, 4)]},
    {'name': 'Жим гантелей сидя', 'description': 'Меньше читинга, чем стоя.', 'main_muscles': [Muscle.DELTOID_ANTERIOR.value, Muscle.DELTOID_LATERAL.value], 'muscle_group': MuscleGroup.SHOULDERS.value, 'approaches': [_ap(None, 10, 3)]},
    {'name': 'Махи гантелями в стороны', 'description': 'Средний пучок.', 'main_muscles': [Muscle.DELTOID_LATERAL.value], 'muscle_group': MuscleGroup.SHOULDERS.value, 'approaches': [_ap(None, 15, 3)]},
    {'name': 'Махи в стороны в кроссовере', 'description': 'Постоянное натяжение.', 'main_muscles': [Muscle.DELTOID_LATERAL.value], 'muscle_group': MuscleGroup.SHOULDERS.value, 'approaches': [_ap(None, 12, 4)]},
    {'name': 'Подъём штанги перед собой', 'description': 'Передняя дельта.', 'main_muscles': [Muscle.DELTOID_ANTERIOR.value], 'muscle_group': MuscleGroup.SHOULDERS.value, 'approaches': [_ap(None, 12, 3)]},
    {'name': 'Разводка гантелей за спину в наклоне', 'description': 'Задняя дельта.', 'main_muscles': [Muscle.DELTOID_POSTERIOR.value], 'muscle_group': MuscleGroup.SHOULDERS.value, 'approaches': [_ap(None, 15, 3)]},
    {'name': 'Эспандер для задней дельты', 'description': 'Лёгкая изоляция.', 'main_muscles': [Muscle.DELTOID_POSTERIOR.value, Muscle.RHOMBOIDS.value], 'muscle_group': MuscleGroup.SHOULDERS.value, 'approaches': [_ap(None, 20, 3)]},
    # Бицепс
    {'name': 'Подъём штанги на бицепс стоя', 'description': 'Базовое упражнение.', 'main_muscles': [Muscle.BICEPS_BRACHII.value, Muscle.BRACHIALIS.value], 'muscle_group': MuscleGroup.BICEPS.value, 'approaches': [_ap(None, 12, 3)]},
    {'name': 'Подъём гантелей на бицепс молот', 'description': 'Кисть нейтральная.', 'main_muscles': [Muscle.BICEPS_BRACHII.value, Muscle.FOREARM_FLEXORS.value], 'muscle_group': MuscleGroup.BICEPS.value, 'approaches': [_ap(None, 12, 4)]},
    {'name': 'Концентрированный подъём на бицепс', 'description': 'Изоляция.', 'main_muscles': [Muscle.BICEPS_BRACHII.value], 'muscle_group': MuscleGroup.BICEPS.value, 'approaches': [_ap(None, 12, 3)]},
    {'name': 'Подъём на бицепс на скамье Скотта', 'description': 'Фиксация плеча.', 'main_muscles': [Muscle.BICEPS_BRACHII.value, Muscle.BRACHIALIS.value], 'muscle_group': MuscleGroup.BICEPS.value, 'approaches': [_ap(None, 10, 4)]},
    {'name': 'Подъём EZ-грифа на бицепс', 'description': 'Удобнее для запястий.', 'main_muscles': [Muscle.BICEPS_BRACHII.value], 'muscle_group': MuscleGroup.BICEPS.value, 'approaches': [_ap(None, 12, 3)]},
    # Трицепс
    {'name': 'Французский жим лёжа', 'description': 'Разгибание локтя.', 'main_muscles': [Muscle.TRICEPS_LONG_HEAD.value], 'muscle_group': MuscleGroup.TRICEPS.value, 'approaches': [_ap(None, 12, 4)]},
    {'name': 'Разгибание каната на блоке', 'description': 'Пиковое сокращение.', 'main_muscles': [Muscle.TRICEPS_LONG_HEAD.value], 'muscle_group': MuscleGroup.TRICEPS.value, 'approaches': [_ap(None, 15, 3)]},
    {'name': 'Отжимания на брусьях с узким хватом', 'description': 'Трицепс и нижняя часть груди.', 'main_muscles': [Muscle.TRICEPS_LONG_HEAD.value, Muscle.PECTORALIS_MAJOR.value], 'muscle_group': MuscleGroup.TRICEPS.value, 'approaches': [_ap(None, 10, 4)]},
    {'name': 'Разгибание руки с гантелью из-за головы', 'description': 'Длинная головка трицепса.', 'main_muscles': [Muscle.TRICEPS_LONG_HEAD.value], 'muscle_group': MuscleGroup.TRICEPS.value, 'approaches': [_ap(None, 12, 3)]},
    {'name': 'Отжимания узким хватом от пола', 'description': 'Локтя вдоль корпуса.', 'main_muscles': [Muscle.TRICEPS_LONG_HEAD.value], 'muscle_group': MuscleGroup.TRICEPS.value, 'approaches': [_ap(None, 12, 3)]},
    # Ноги
    {'name': 'Приседания со штангой на спине', 'description': 'Базовое комплексное.', 'main_muscles': [Muscle.QUADRICEPS.value, Muscle.GLUTEUS_MAXIMUS.value], 'muscle_group': MuscleGroup.LEGS.value, 'approaches': [_ap(None, 8, 4)]},
    {'name': 'Фронтальные приседания', 'description': 'Больший акцент на квадрицепс.', 'main_muscles': [Muscle.QUADRICEPS.value], 'muscle_group': MuscleGroup.LEGS.value, 'approaches': [_ap(None, 10, 4)]},
    {'name': 'Жим ногами в тренажёре', 'description': 'Без осевой нагрузки на позвоночник.', 'main_muscles': [Muscle.QUADRICEPS.value, Muscle.GLUTEUS_MAXIMUS.value], 'muscle_group': MuscleGroup.LEGS.value, 'approaches': [_ap(None, 12, 4)]},
    {'name': 'Разгибания ног сидя', 'description': 'Изоляция квадрицепса.', 'main_muscles': [Muscle.QUADRICEPS.value], 'muscle_group': MuscleGroup.LEGS.value, 'approaches': [_ap(None, 15, 3)]},
    {'name': 'Выпады шагающие с гантелями', 'description': 'Стабилизация и ягодицы.', 'main_muscles': [Muscle.QUADRICEPS.value, Muscle.GLUTEUS_MAXIMUS.value], 'muscle_group': MuscleGroup.LEGS.value, 'approaches': [_ap(None, 12, 3)]},
    {'name': 'Болгарские выпады', 'description': 'Одна нога за скамьёй.', 'main_muscles': [Muscle.QUADRICEPS.value, Muscle.GLUTEUS_MAXIMUS.value], 'muscle_group': MuscleGroup.LEGS.value, 'approaches': [_ap(None, 10, 3)]},
    {'name': 'Румынская тяга со штангой', 'description': 'Задняя поверхность бедра.', 'main_muscles': [Muscle.HAMSTRINGS.value, Muscle.ERECTOR_SPINAE.value], 'muscle_group': MuscleGroup.LEGS.value, 'approaches': [_ap(None, 10, 4)]},
    {'name': 'Сгибания ног лёжа', 'description': 'Изоляция бицепса бедра.', 'main_muscles': [Muscle.HAMSTRINGS.value], 'muscle_group': MuscleGroup.LEGS.value, 'approaches': [_ap(None, 12, 3)]},
    {'name': 'Подъёмы на носки стоя со штангой', 'description': 'Икры со свободными весами.', 'main_muscles': [Muscle.GASTROCNEMIUS.value, Muscle.SOLEUS.value], 'muscle_group': MuscleGroup.LEGS.value, 'approaches': [_ap(None, 15, 4)]},
    {'name': 'Подъёмы на носки сидя в тренажёре', 'description': 'Камбаловидная.', 'main_muscles': [Muscle.SOLEUS.value], 'muscle_group': MuscleGroup.LEGS.value, 'approaches': [_ap(None, 20, 3)]},
    # Пресс / кор
    {'name': 'Скручивания лёжа', 'description': 'Прямая мышца живота.', 'main_muscles': [Muscle.RECTUS_ABDOMINIS.value], 'muscle_group': MuscleGroup.CORE.value, 'approaches': [_ap(None, 20, 3)]},
    {'name': 'Подъём коленей в висе', 'description': 'Низ живота.', 'main_muscles': [Muscle.RECTUS_ABDOMINIS.value], 'muscle_group': MuscleGroup.CORE.value, 'approaches': [_ap(None, 15, 3)]},
    {'name': 'Планка классическая', 'description': 'Статика кора (держать позицию в каждом подходе).', 'main_muscles': [Muscle.RECTUS_ABDOMINIS.value, Muscle.OBLIQUES.value], 'muscle_group': MuscleGroup.CORE.value, 'approaches': [_ap(None, 3, 3)]},
    {'name': 'Боковая планка', 'description': 'Косые.', 'main_muscles': [Muscle.OBLIQUES.value], 'muscle_group': MuscleGroup.CORE.value, 'approaches': [_ap(None, 3, 3)]},
    {'name': 'Велосипед лёжа', 'description': 'Попеременные скручивания.', 'main_muscles': [Muscle.RECTUS_ABDOMINIS.value, Muscle.OBLIQUES.value], 'muscle_group': MuscleGroup.CORE.value, 'approaches': [_ap(None, 20, 3)]},
    # Ягодицы
    {'name': 'Ягодичный мостик со штангой', 'description': 'Разгибание бедра.', 'main_muscles': [Muscle.GLUTEUS_MAXIMUS.value, Muscle.HAMSTRINGS.value], 'muscle_group': MuscleGroup.GLUTES.value, 'approaches': [_ap(None, 12, 4)]},
    {'name': 'Зашагивания на платформу с гантелями', 'description': 'Ягодицы и квадрицепс.', 'main_muscles': [Muscle.GLUTEUS_MAXIMUS.value, Muscle.QUADRICEPS.value], 'muscle_group': MuscleGroup.GLUTES.value, 'approaches': [_ap(None, 12, 3)]},
    {'name': 'Отведение ноги назад в кроссовере', 'description': 'Изоляция ягодиц.', 'main_muscles': [Muscle.GLUTEUS_MAXIMUS.value], 'muscle_group': MuscleGroup.GLUTES.value, 'approaches': [_ap(None, 15, 3)]},
    {'name': 'Гиперэкстензия с акцентом на ягодицы', 'description': 'Разгибание бедра.', 'main_muscles': [Muscle.GLUTEUS_MAXIMUS.value, Muscle.HAMSTRINGS.value], 'muscle_group': MuscleGroup.GLUTES.value, 'approaches': [_ap(None, 15, 3)]},
    # Икры
    {'name': 'Прыжки на скакалке', 'description': 'Выносливость голени.', 'main_muscles': [Muscle.GASTROCNEMIUS.value, Muscle.SOLEUS.value], 'muscle_group': MuscleGroup.CALVES.value, 'approaches': [_ap(None, 100, 3)]},
    {'name': 'Подъёмы на носки в Гакк-тренажёре', 'description': 'Тяжёлая нагрузка на икры.', 'main_muscles': [Muscle.GASTROCNEMIUS.value], 'muscle_group': MuscleGroup.CALVES.value, 'approaches': [_ap(None, 15, 4)]},
    {'name': 'Одноногие подъёмы на носки', 'description': 'Устранение перекосов.', 'main_muscles': [Muscle.GASTROCNEMIUS.value, Muscle.SOLEUS.value], 'muscle_group': MuscleGroup.CALVES.value, 'approaches': [_ap(None, 15, 3)]},
    # Full body
    {'name': 'Становая тяга классическая', 'description': 'Задняя цепь.', 'main_muscles': [Muscle.ERECTOR_SPINAE.value, Muscle.GLUTEUS_MAXIMUS.value, Muscle.HAMSTRINGS.value, Muscle.TRAPEZIUS.value], 'muscle_group': MuscleGroup.FULL_BODY.value, 'approaches': [_ap(None, 5, 5)]},
    {'name': 'Становая тяга сумо', 'description': 'Широкая постановка ног.', 'main_muscles': [Muscle.GLUTEUS_MAXIMUS.value, Muscle.HAMSTRINGS.value, Muscle.QUADRICEPS.value], 'muscle_group': MuscleGroup.FULL_BODY.value, 'approaches': [_ap(None, 6, 4)]},
]


_names = [row['name'] for row in GLOBAL_EXERCISES_SEED]
if len(_names) != len(set(_names)):
    raise ValueError('Дубликаты имён в GLOBAL_EXERCISES_SEED')
if len(GLOBAL_EXERCISES_SEED) < 50:
    raise ValueError('Ожидалось не менее 50 упражнений в сиде')


class Command(BaseCommand):
    help = (
        'Добавляет глобальные упражнения (Exercise без пользователя). '
        'Повторный запуск по умолчанию пропускает уже существующие строки с тем же именем.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Обновить описание, main_muscles, muscle_group и approaches у совпавших по имени глобальных записей.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        update_existing = options['update_existing']
        created = 0
        skipped = 0
        updated = 0

        for row in GLOBAL_EXERCISES_SEED:
            defaults = {
                'description': row['description'],
                'main_muscles': row['main_muscles'],
                'muscle_group': row['muscle_group'],
                'approaches': row['approaches'],
            }
            obj, was_created = Exercise.objects.get_or_create(
                name=row['name'],
                user=None,
                defaults=defaults,
            )
            if was_created:
                created += 1
                continue
            if update_existing:
                for field, value in defaults.items():
                    setattr(obj, field, value)
                obj.save()
                updated += 1
            else:
                skipped += 1

        total_global = Exercise.objects.filter(user__isnull=True).count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Готово: создано {created}, пропущено {skipped}, обновлено {updated}. '
                f'Всего глобальных упражнений в БД: {total_global}.'
            )
        )
