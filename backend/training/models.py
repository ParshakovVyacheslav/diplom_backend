import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
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


class AssignmentTemplate(models.Model):
    """Шаблон тренировки: набор сетов подходов и правила по дням недели."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assignment_templates',
    )
    name = models.CharField(max_length=255)
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text='Дата окончания действия шаблона; пусто — без ограничения по дате.',
    )
    days_of_week = models.JSONField(
        default=list,
        help_text='Дни недели, когда применяется шаблон: список целых 0–6 (пн–вс).',
    )

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['user', 'name']),
        ]
        verbose_name = 'шаблон назначения тренировки'
        verbose_name_plural = 'шаблоны назначений тренировок'

    def __str__(self):
        return self.name


class WorkoutSet(models.Model):
    """Именованный набор подходов внутри шаблона (порядок задаётся полем order)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        AssignmentTemplate,
        on_delete=models.CASCADE,
        related_name='workout_sets',
    )
    name = models.CharField(max_length=255, blank=True, default='')
    order = models.PositiveSmallIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['template', 'order']),
        ]
        verbose_name = 'набор подходов (сет)'
        verbose_name_plural = 'наборы подходов (сеты)'

    def __str__(self):
        return self.name or f'Set #{self.order}'


class Approach(models.Model):
    """Подход в рамках сета: упражнение, вес, повторения, число рабочих сетов."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workout_set = models.ForeignKey(
        WorkoutSet,
        on_delete=models.CASCADE,
        related_name='approaches',
    )
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name='template_approaches',
    )
    weight_kg = models.FloatField(
        null=True,
        blank=True,
        help_text='Вес в кг; пусто — по плану / собственный вес.',
    )
    reps = models.PositiveIntegerField(help_text='Повторения в одном рабочем сете.')
    sets_count = models.PositiveIntegerField(help_text='Количество рабочих сетов с этими параметрами.')
    order = models.PositiveSmallIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['workout_set', 'order']),
        ]
        verbose_name = 'подход'
        verbose_name_plural = 'подходы'

    def clean(self):
        super().clean()
        if not self.workout_set_id or not self.exercise_id:
            return
        owner_id = self.workout_set.template.user_id
        ex_user = self.exercise.user_id
        if ex_user is not None and ex_user != owner_id:
            raise ValidationError({'exercise': 'Личное упражнение должно принадлежать владельцу шаблона.'})

    def __str__(self):
        return f'{self.exercise.name} ×{self.sets_count}@{self.reps}'


class Assignment(models.Model):
    """Запланированная тренировка: дата + шаблон, по которому она проводится."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    template = models.ForeignKey(
        AssignmentTemplate,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    date = models.DateField(db_index=True)

    class Meta:
        ordering = ['-date', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'template', 'date'],
                name='uniq_training_assignment_user_template_date',
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'date']),
        ]
        verbose_name = 'назначение тренировки'
        verbose_name_plural = 'назначения тренировок'

    def clean(self):
        super().clean()
        if self.template_id and self.user_id and self.template.user_id != self.user_id:
            raise ValidationError({'template': 'Шаблон принадлежит другому пользователю.'})

    def __str__(self):
        return f'{self.date} — {self.template.name}'
