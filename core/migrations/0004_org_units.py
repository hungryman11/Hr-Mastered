from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_leave_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrgUnit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('name', models.CharField(max_length=255)),
                ('unit_type', models.CharField(choices=[('BOARD', 'Board'), ('EXECUTIVE', 'Executive'), ('DIVISION', 'Division'), ('DEPARTMENT', 'Department'), ('TEAM', 'Team'), ('FUNCTION', 'Function')], max_length=20)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_records', to='core.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to='core.employee')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to='core.employee')),
                ('head', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='led_org_units', to='core.employee')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to='core.orgunit')),
            ],
            options={
                'db_table': 'org_units',
                'ordering': ('sort_order', 'name'),
                'unique_together': {('company', 'parent', 'name')},
            },
        ),
    ]
