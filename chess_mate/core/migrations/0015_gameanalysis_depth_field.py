from django.db import migrations, models


def add_depth_column_if_missing(apps, schema_editor):
    table_name = "core_gameanalysis"
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())

    if table_name not in existing_tables:
        game_analysis_model = apps.get_model("core", "GameAnalysis")
        schema_editor.create_model(game_analysis_model)
        with connection.cursor() as cursor:
            cursor.execute(
                f"ALTER TABLE {schema_editor.quote_name(table_name)} ADD COLUMN depth integer"
            )
        return

    with connection.cursor() as cursor:
        columns = {
            col.name
            for col in connection.introspection.get_table_description(
                cursor, table_name
            )
        }
        if "depth" not in columns:
            cursor.execute(
                f"ALTER TABLE {schema_editor.quote_name(table_name)} ADD COLUMN depth integer"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_payment_amount_float"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_depth_column_if_missing, migrations.RunPython.noop
                ),
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
