from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations
from django.contrib.postgres.indexes import GinIndex


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        TrigramExtension(),
        migrations.AddIndex(
            model_name='product',
            index=GinIndex(
                fields=['name'],
                opclasses=['gin_trgm_ops'],
                name='product_name_trgm_gin_idx',
            ),
        ),
    ]
