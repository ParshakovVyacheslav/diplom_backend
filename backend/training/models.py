import uuid

from django.conf import settings
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
