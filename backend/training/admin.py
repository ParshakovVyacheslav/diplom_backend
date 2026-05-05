from django.contrib import admin

from .models import DayCompletion, Exercise, TemplateAssignment, WorkoutTemplate


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'muscle_group')
    list_filter = ('muscle_group', 'user')


@admin.register(WorkoutTemplate)
class WorkoutTemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'kind')
    list_filter = ('kind',)


@admin.register(TemplateAssignment)
class TemplateAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'template', 'anchor_date', 'interval_days', 'end_date', 'sort_order')


@admin.register(DayCompletion)
class DayCompletionAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'completed')
