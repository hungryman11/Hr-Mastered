from django.db import migrations, models
import decimal


def migrate_config_to_items(apps, schema_editor):
    KpiFramework = apps.get_model('core', 'KpiFramework')
    KpiTemplate = apps.get_model('core', 'KpiTemplate')
    KpiFrameworkItem = apps.get_model('core', 'KpiFrameworkItem')

    for fw in KpiFramework.objects.all():
        config = fw.configuration or {}
        # Only migrate if there are no existing items and configuration is a list
        if getattr(fw, 'items', None) is not None and fw.items.exists():
            continue
        if isinstance(config, list) and len(config) > 0:
            seq = 0
            for entry in config:
                template_id = entry.get('template')
                if not template_id:
                    continue
                # Try to resolve template by UUID string or integer PK
                template = None
                try:
                    template = KpiTemplate.objects.get(uuid=template_id)
                except Exception:
                    try:
                        template = KpiTemplate.objects.get(pk=int(template_id))
                    except Exception:
                        continue
                weight = entry.get('weight', 0)
                try:
                    weight = decimal.Decimal(str(weight))
                except Exception:
                    weight = decimal.Decimal('0')
                target = entry.get('target', '') or ''
                KpiFrameworkItem.objects.create(framework_id=fw.id, template_id=template.id, weight=weight, target=target, sequence=seq)
                seq += 1


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_add_kpiframeworkitem'),
    ]

    operations = [
        migrations.RunPython(migrate_config_to_items, reverse_code=migrations.RunPython.noop),
    ]
