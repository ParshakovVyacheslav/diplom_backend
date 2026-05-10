import uuid

from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0006_assignment_approach_progress'),
    ]

    operations = [
        migrations.AddField(
            model_name='workoutset',
            name='rounds',
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text='Сколько «кругов» сета запланировано; остаток по конкретному назначению — в AssignmentWorkoutSetProgress.',
            ),
        ),
        migrations.CreateModel(
            name='AssignmentWorkoutSetProgress',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    'rounds_remains',
                    models.IntegerField(
                        default=1,
                        help_text='Оставшиеся круги (0 — закончен); если записи нет, клиент считает равным workout_set.rounds.',
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    'assignment',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='workout_set_progress',
                        to='training.assignment',
                    ),
                ),
                (
                    'workout_set',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='assignment_set_progress',
                        to='training.workoutset',
                    ),
                ),
            ],
            options={
                'verbose_name': 'прогресс сета по назначению',
                'verbose_name_plural': 'прогресс сетов по назначениям',
            },
        ),
        migrations.AddConstraint(
            model_name='assignmentworkoutsetprogress',
            constraint=models.UniqueConstraint(
                fields=('assignment', 'workout_set'),
                name='uniq_training_assignment_workout_set_progress',
            ),
        ),
    ]
