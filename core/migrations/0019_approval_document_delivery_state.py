from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0018_delivery_job_model_state')]

    operations = [
        migrations.AddField(model_name='approvaldocument', name='upload_error', field=models.TextField(blank=True)),
        migrations.AddField(model_name='approvaldocument', name='upload_status', field=models.CharField(default='PENDING', max_length=20)),
        migrations.AddField(model_name='approvaldocument', name='zoho_file_id', field=models.CharField(blank=True, max_length=150, null=True)),
    ]
