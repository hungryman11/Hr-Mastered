from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_leave_approval_steps_and_roles'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaverequest',
            name='contact_during_leave',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='emergency_contact_name',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='emergency_contact_phone',
            field=models.CharField(default='', max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='handover_contact',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='handover_notes',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='supporting_document_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='supporting_zoho_file_id',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='supporting_workdrive_url',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]
