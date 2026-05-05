import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models


class MuscleGroup(models.TextChoices):
    CHEST = 'Chest'
    BACK = 'Back'
    SHOULDERS = 'Shoulders'
    BICEPS = 'Biceps'
    TRICEPS = 'Triceps'
    LEGS = 'Legs'
    CORE = 'Core'
    GLUTES = 'Glutes'
    CALVES = 'Calves'
    FULL_BODY = 'FullBody'


class Muscle(models.TextChoices):
    PECTORALIS_MAJOR = 'PectoralisMajor'
    LATISSIMUS_DORSI = 'LatissimusDorsi'
    TRAPEZIUS = 'Trapezius'
    RHOMBOIDS = 'Rhomboids'
    DELTOID_ANTERIOR = 'DeltoidAnterior'
    DELTOID_LATERAL = 'DeltoidLateral'
    DELTOID_POSTERIOR = 'DeltoidPosterior'
    BICEPS_BRACHII = 'BicepsBrachii'
    TRICEPS_LONG_HEAD = 'TricepsLongHead'
    BRACHIALIS = 'Brachialis'
    QUADRICEPS = 'Quadriceps'
    HAMSTRINGS = 'Hamstrings'
    GLUTEUS_MAXIMUS = 'GluteusMaximus'
    GASTROCNEMIUS = 'Gastrocnemius'
    SOLEUS = 'Soleus'
    RECTUS_ABDOMINIS = 'RectusAbdominis'
    OBLIQUES = 'Obliques'
    ERECTOR_SPINAE = 'ErectorSpinae'
    FOREARM_FLEXORS = 'ForearmFlexors'


class TemplateKind(models.TextChoices):
    PLAN = 'plan'
    SET = 'set'


class Exercise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='personal_exercises',
        null=True,
        blank=True,
        db_index=True,
        help_text='null — глобальное упражнение',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    main_muscles = models.JSONField(default=list)
    muscle_group = models.CharField(max_length=32, choices=MuscleGroup.choices)
    approaches = models.JSONField(default=list)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'name']),
            models.Index(fields=['muscle_group']),
        ]

    def __str__(self):
        return self.name


class WorkoutTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workout_templates',
    )
    kind = models.CharField(max_length=8, choices=TemplateKind.choices)
    name = models.CharField(max_length=255)
    nodes = models.JSONField(default=list)
    muscle_groups = ArrayField(
        models.CharField(max_length=32),
        default=list,
        blank=True,
        help_text='Группы мышц из упражнений узлов (для фильтра /api/sets)',
    )

    class Meta:
        indexes = [
            models.Index(fields=['user', 'kind']),
            models.Index(fields=['user', 'kind', 'name']),
        ]

    def __str__(self):
        return self.name


class TemplateAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='template_assignments',
    )
    template = models.ForeignKey(
        WorkoutTemplate,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    anchor_date = models.DateField()
    interval_days = models.PositiveIntegerField()
    end_date = models.DateField(blank=True, null=True)
    sort_order = models.IntegerField()

    class Meta:
        ordering = ['sort_order', 'anchor_date']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['user', 'sort_order']),
        ]

    def __str__(self):
        return f'{self.template.name} → {self.anchor_date}'


class DayCompletion(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='training_day_completions',
    )
    date = models.DateField()
    completed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'date'], name='uniq_training_daycompletion_user_date'),
        ]

    def __str__(self):
        return f'{self.user_id} {self.date} completed={self.completed}'
