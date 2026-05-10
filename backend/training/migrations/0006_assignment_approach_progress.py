import uuid

from django.db import migrations, models
import django.db.models.deletion


def copy_approach_done_to_progress(apps, schema_editor):
    Approach = apps.get_model('training', 'Approach')
    Assignment = apps.get_model('training', 'Assignment')
    Progress = apps.get_model('training', 'AssignmentApproachProgress')
    batch = []
    batch_size = 500
    for approach in Approach.objects.select_related('workout_set').iterator(chunk_size=200):
        template_id = approach.workout_set.template_id
        flag = approach.is_done
        for aid in Assignment.objects.filter(template_id=template_id).values_list('id', flat=True):
            batch.append(
                Progress(
                    id=uuid.uuid4(),
                    assignment_id=aid,
                    approach_id=approach.id,
                    is_done=flag,
                )
            )
            if len(batch) >= batch_size:
                Progress.objects.bulk_create(batch, batch_size=batch_size)
                batch.clear()
    if batch:
        Progress.objects.bulk_create(batch, batch_size=batch_size)


def merge_progress_into_approach_is_done(apps, schema_editor):
    Approach = apps.get_model('training', 'Approach')
    Progress = apps.get_model('training', 'AssignmentApproachProgress')
    for approach in Approach.objects.iterator(chunk_size=500):
        done = Progress.objects.filter(approach_id=approach.id, is_done=True).exists()
        if approach.is_done != done:
            approach.is_done = done
            approach.save(update_fields=['is_done'])


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0005_assignmenttemplate_is_active'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssignmentApproachProgress',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('is_done', models.BooleanField(db_index=True, default=False)),
                (
                    'approach',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='assignment_progress',
                        to='training.approach',
                    ),
                ),
                (
                    'assignment',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='approach_progress',
                        to='training.assignment',
                    ),
                ),
            ],
            options={
                'verbose_name': 'прогресс подхода по назначению',
                'verbose_name_plural': 'прогресс подходов по назначениям',
            },
        ),
        migrations.AddConstraint(
            model_name='assignmentapproachprogress',
            constraint=models.UniqueConstraint(
                fields=('assignment', 'approach'),
                name='uniq_training_assignment_approach_progress',
            ),
        ),
        migrations.RunPython(copy_approach_done_to_progress, merge_progress_into_approach_is_done),
        migrations.RemoveField(
            model_name='approach',
            name='is_done',
        ),
    ]
