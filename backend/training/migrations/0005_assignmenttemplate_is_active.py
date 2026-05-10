from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0004_approach_assignment_is_done'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignmenttemplate',
            name='is_active',
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text='Если выключено, назначения (Assignment) по шаблону не ведутся; существующие удаляются.',
            ),
        ),
    ]
