import django.db.models.deletion
import uuid

from django.db import migrations, models
import core.models.calendar


class Migration(migrations.Migration):
    dependencies = [('core', '0022_align_holiday_model_state')]

    operations = [
        migrations.CreateModel(
            name='CompanyWorkCalendar',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('working_weekdays', models.JSONField(default=core.models.calendar.default_working_weekdays)),
                ('include_nigerian_public_holidays', models.BooleanField(default=True)),
                ('company', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='work_calendar', to='core.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='companyworkcalendar_created_by', to='core.employee')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='companyworkcalendar_updated_by', to='core.employee')),
            ],
            options={'db_table': 'company_work_calendars'},
        ),
    ]
