from django.contrib import admin

from .models import Exercise


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'muscle_group')
    list_filter = ('muscle_group', 'user')
