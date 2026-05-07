from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(name='TemplateAssignment'),
        migrations.DeleteModel(name='WorkoutTemplate'),
        migrations.DeleteModel(name='DayCompletion'),
    ]
