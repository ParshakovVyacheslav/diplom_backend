"""Генерация Assignment по календарю для AssignmentTemplate."""

from datetime import date, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Approach, Assignment, AssignmentTemplate, WorkoutSet


def _schedule_horizon_days() -> int:
    return int(getattr(settings, 'TRAINING_SCHEDULE_DEFAULT_DAYS', 365))


def normalized_days_of_week(days):
    """Проверка и нормализация набора будних дней 0–6 (пн–вс)."""
    if not isinstance(days, (list, tuple)) or len(days) == 0:
        raise ValueError('Должен быть непустой список дней недели (0–6, пн–вс)')
    normalized = tuple(sorted({int(x) for x in days}))
    for d in normalized:
        if d < 0 or d > 6:
            raise ValueError(f'День недели должен быть 0–6, получено {d}')
    return normalized


def _schedule_end_exclusive(start: date, template_end: date | None) -> date:
    """Верхняя граница (не включается) для перебора дат."""
    horizon = start + timedelta(days=_schedule_horizon_days())
    if template_end is not None:
        return min(template_end + timedelta(days=1), horizon)
    return horizon


def iter_schedule_dates(days_of_week, start: date, template_end: date | None):
    normalized_days_of_week(days_of_week)
    allowed = set(int(x) for x in days_of_week)
    cur = start
    end_exclusive = _schedule_end_exclusive(start, template_end)
    while cur < end_exclusive:
        if cur.weekday() in allowed:
            yield cur
        cur += timedelta(days=1)


def _persist_approaches_for_set(ws: WorkoutSet, approaches_payload: list[dict]):
    sorted_appr = sorted(enumerate(approaches_payload), key=lambda it: int(it[1].get('order', it[0])))
    for j, a in sorted_appr:
        appr = Approach(
            workout_set=ws,
            exercise_id=a['exerciseId'],
            weight_kg=a.get('weightKg'),
            reps=int(a['reps']),
            sets_count=int(a['setsCount']),
            order=int(a.get('order', j)),
        )
        appr.full_clean()
        appr.save()


@transaction.atomic
def create_scheduled_assignment_template(user, validated: dict) -> AssignmentTemplate:
    """Создание шаблона из валидированного тела POST: сеты + генерация календаря."""

    start_date = validated.get('scheduleStartDate') or timezone.now().date()
    tmpl = AssignmentTemplate.objects.create(
        user=user,
        name=validated['name'],
        end_date=validated.get('endDate'),
        days_of_week=validated['daysOfWeek'],
        is_active=bool(validated.get('isActive', True)),
    )
    persist_workout_sets_for_template(tmpl, validated['sets'])
    reschedule_assignments_for_template(tmpl, start_date)
    return tmpl


@transaction.atomic
def persist_workout_sets_for_template(template: AssignmentTemplate, sets_payload: list[dict]):
    """Полная замена сетов подходов у шаблона (старое удаляется каскадно)."""

    WorkoutSet.objects.filter(template=template).delete()

    sorted_payload = sorted(enumerate(sets_payload), key=lambda it: int(it[1].get('order', it[0])))
    for i, s in sorted_payload:
        order = int(s.get('order', i))
        rounds = int(s.get('rounds', 1))
        if rounds < 1:
            raise ValueError('В каждом сете rounds должно быть >= 1')
        ws = WorkoutSet.objects.create(
            template=template,
            name=(s.get('name') or '')[:255],
            order=order,
            rounds=rounds,
        )
        appr_list = s.get('approaches') or []
        if len(appr_list) == 0:
            raise ValueError('В каждом сете нужен хотя бы один подход')
        _persist_approaches_for_set(ws, appr_list)


@transaction.atomic
def reschedule_assignments_for_template(template: AssignmentTemplate, start: date):
    """Удалить все Assignment по шаблону; при активном шаблоне заново создать по календарю."""

    Assignment.objects.filter(template=template).delete()
    if not template.is_active:
        return
    today = timezone.now().date()
    anchor = max(start, today)
    bulk = []
    for d in iter_schedule_dates(template.days_of_week, anchor, template.end_date):
        bulk.append(Assignment(user_id=template.user_id, template_id=template.id, date=d))
    if bulk:
        Assignment.objects.bulk_create(bulk)


@transaction.atomic
def replace_assignments_for_day(user, workout_date: date, payload: dict) -> AssignmentTemplate:
    """Удалить все назначения пользователя на дату; создать новый шаблон с сетами и одну тренировку."""

    Assignment.objects.filter(user=user, date=workout_date).delete()
    raw_name = payload.get('name')
    if isinstance(raw_name, str):
        tmpl_name = raw_name.strip() or f'Тренировка {workout_date.isoformat()}'
    else:
        tmpl_name = f'Тренировка {workout_date.isoformat()}'
    tmpl = AssignmentTemplate.objects.create(
        user=user,
        name=tmpl_name[:255],
        end_date=payload.get('endDate'),
        days_of_week=payload.get('daysOfWeek') or [workout_date.weekday()],
        is_active=True,
    )
    persist_workout_sets_for_template(tmpl, payload['sets'])
    ass = Assignment(user=user, template=tmpl, date=workout_date)
    ass.full_clean()
    ass.save()
    return tmpl
