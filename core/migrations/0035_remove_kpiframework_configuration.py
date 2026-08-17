from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_migrate_framework_configuration_to_items'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='kpiframework',
            name='configuration',
        ),
    ]
