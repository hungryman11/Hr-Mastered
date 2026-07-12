from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='department',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='employees', to='core.department'),
        ),
        migrations.AddField(
            model_name='employee',
            name='role',
            field=models.CharField(choices=[('HR_ADMIN', 'HR Admin'), ('MANAGER', 'Manager'), ('EMPLOYEE', 'Employee')], default='EMPLOYEE', max_length=20),
        ),
        migrations.AddField(
            model_name='employee',
            name='manager',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='direct_reports', to='core.employee'),
        ),
    ]
