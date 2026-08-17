from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0037_snapshot_assignment_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeekpiassignment',
            name='template_description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='employeekpiassignment',
            name='template_default_target',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='employeekpiassignment',
            name='template_default_weight',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='employeekpiassignment',
            name='template_frequency',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='employeekpiassignment',
            name='template_data_source',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
