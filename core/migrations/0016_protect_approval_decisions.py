from django.db import migrations


POSTGRES_CREATE_TRIGGER = """
CREATE OR REPLACE FUNCTION core_prevent_approval_decision_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'approval_decisions are immutable';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS approval_decisions_immutable ON approval_decisions;
CREATE TRIGGER approval_decisions_immutable
BEFORE UPDATE OR DELETE ON approval_decisions
FOR EACH ROW EXECUTE FUNCTION core_prevent_approval_decision_mutation();
"""

POSTGRES_DROP_TRIGGER = """
DROP TRIGGER IF EXISTS approval_decisions_immutable ON approval_decisions;
DROP FUNCTION IF EXISTS core_prevent_approval_decision_mutation();
"""


def create_postgres_trigger(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(POSTGRES_CREATE_TRIGGER)


def drop_postgres_trigger(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(POSTGRES_DROP_TRIGGER)


class Migration(migrations.Migration):
    dependencies = [('core', '0015_leavetype_requires_supporting_document')]

    operations = [migrations.RunPython(create_postgres_trigger, drop_postgres_trigger)]
