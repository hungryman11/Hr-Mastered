from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_org_units'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='org_unit',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='employees', to='core.orgunit'),
        ),
    ]
