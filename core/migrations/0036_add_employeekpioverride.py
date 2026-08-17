from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_remove_kpiframework_configuration'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmployeeKpiOverride',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('weight', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('target', models.CharField(blank=True, max_length=100)),
                ('active', models.BooleanField(default=True)),
                ('effective_from', models.DateField(blank=True, null=True)),
                ('effective_to', models.DateField(blank=True, null=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kpi_overrides', to='core.employee')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.kpitemplate')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='employeekpioverride_records', to='core.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='employeekpioverride_created_by', to='core.employee')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='employeekpioverride_updated_by', to='core.employee')),
            ],
            options={
                'db_table': 'employee_kpi_overrides',
            },
        ),
        migrations.AlterUniqueTogether(
            name='employeekpioverride',
            unique_together={('employee', 'template')},
        ),
    ]
