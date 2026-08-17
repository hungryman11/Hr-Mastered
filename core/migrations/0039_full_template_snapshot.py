from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_snapshot_more_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeekpiassignment',
            name='full_template_snapshot',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
