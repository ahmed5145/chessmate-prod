from django.db import migrations, models


def add_depth_column_if_missing(apps, schema_editor):
    table_name = "core_gameanalysis"
    with schema_editor.connection.cursor() as cursor:
        columns = {
            col.name for col in schema_editor.connection.introspection.get_table_description(cursor, table_name)
        }
        if "depth" not in columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN depth integer")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_payment_amount_float"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_depth_column_if_missing, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="gameanalysis",
                    name="depth",
                    field=models.IntegerField(blank=True, default=20, null=True),
                ),
            ],
        ),
    ]
