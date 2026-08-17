from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_add_employeekpioverride'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeekpiassignment',
            name='template_name',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='employeekpiassignment',
            name='measurement_type',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='employeekpiassignment',
            name='direction',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='employeekpiassignment',
            name='scoring_method',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='employeekpiassignment',
            name='category_name',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]
