# Generated manually for AssignmentTemplate → WorkoutSet → Approach graph and Assignment

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('training', '0002_remove_workouttemplate_templateassignment_daycompletion'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssignmentTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('end_date', models.DateField(blank=True, help_text='Дата окончания действия шаблона; пусто — без ограничения по дате.', null=True)),
                ('days_of_week', models.JSONField(default=list, help_text='Дни недели, когда применяется шаблон: список целых 0–6 (пн–вс).')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignment_templates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'шаблон назначения тренировки',
                'verbose_name_plural': 'шаблоны назначений тренировок',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Assignment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date', models.DateField(db_index=True)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='training.assignmenttemplate')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'назначение тренировки',
                'verbose_name_plural': 'назначения тренировок',
                'ordering': ['-date', 'id'],
            },
        ),
        migrations.CreateModel(
            name='WorkoutSet',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, default='', max_length=255)),
                ('order', models.PositiveSmallIntegerField(db_index=True, default=0)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workout_sets', to='training.assignmenttemplate')),
            ],
            options={
                'verbose_name': 'набор подходов (сет)',
                'verbose_name_plural': 'наборы подходов (сеты)',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Approach',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('weight_kg', models.FloatField(blank=True, help_text='Вес в кг; пусто — по плану / собственный вес.', null=True)),
                ('reps', models.PositiveIntegerField(help_text='Повторения в одном рабочем сете.')),
                ('sets_count', models.PositiveIntegerField(help_text='Количество рабочих сетов с этими параметрами.')),
                ('order', models.PositiveSmallIntegerField(db_index=True, default=0)),
                ('exercise', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='template_approaches', to='training.exercise')),
                ('workout_set', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approaches', to='training.workoutset')),
            ],
            options={
                'verbose_name': 'подход',
                'verbose_name_plural': 'подходы',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='assignment',
            constraint=models.UniqueConstraint(fields=('user', 'template', 'date'), name='uniq_training_assignment_user_template_date'),
        ),
        migrations.AddIndex(
            model_name='assignmenttemplate',
            index=models.Index(fields=['user', 'name'], name='training_as_user_id_0918b3_idx'),
        ),
        migrations.AddIndex(
            model_name='assignment',
            index=models.Index(fields=['user', 'date'], name='training_as_user_id_8ae94d_idx'),
        ),
        migrations.AddIndex(
            model_name='workoutset',
            index=models.Index(fields=['template', 'order'], name='training_wo_templat_30385b_idx'),
        ),
        migrations.AddIndex(
            model_name='approach',
            index=models.Index(fields=['workout_set', 'order'], name='training_ap_workout_e69b76_idx'),
        ),
    ]
