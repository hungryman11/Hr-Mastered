from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_add_position_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='KpiFrameworkItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weight', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('target', models.CharField(blank=True, max_length=100)),
                ('scoring_method_override', models.CharField(blank=True, max_length=100)),
                ('direction_override', models.CharField(blank=True, max_length=20)),
                ('sequence', models.IntegerField(default=0)),
                ('required', models.BooleanField(default=False)),
                ('framework', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='core.kpiframework')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.kpitemplate')),
            ],
            options={
                'db_table': 'kpi_framework_items',
            },
        ),
        migrations.AlterUniqueTogether(
            name='kpiframeworkitem',
            unique_together={('framework', 'template')},
        ),
    ]
