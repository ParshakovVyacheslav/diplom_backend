from datetime import date

from django.db.models import Q
from django.utils import timezone

from .models import DayCompletion, TemplateAssignment


def assignment_matches_calendar_day(assignment: TemplateAssignment, d: date) -> bool:
    if assignment.end_date is not None and d > assignment.end_date:
        return False
    anchor = assignment.anchor_date
    if assignment.interval_days == 0:
        return d == anchor
    if d < anchor:
        return False
    delta = (d - anchor).days
    return delta % assignment.interval_days == 0


def active_assignments_filter_queryset(qs, ref_date: date):
    return qs.filter(Q(end_date__isnull=True) | Q(end_date__gte=ref_date))


def assignments_for_day(user, d: date):
    qs = TemplateAssignment.objects.filter(user=user).select_related('template')
    qs = active_assignments_filter_queryset(qs, d)
    return [a for a in qs if assignment_matches_calendar_day(a, d)]


def day_completed_flag(user, d: date) -> bool:
    row = DayCompletion.objects.filter(user=user, date=d).first()
    return bool(row and row.completed)


def utc_today() -> date:
    return timezone.now().date()
