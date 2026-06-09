"""Backfill and default legacy core_profile.rating on production databases.

Some RDS instances still have a NOT NULL rating column that Django did not map,
which caused signup INSERTs to fail with a null constraint violation.
"""

from django.db import migrations, models


def fix_legacy_rating_column(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS rating integer"
        )
        cursor.execute(
            """
            UPDATE core_profile
            SET rating = COALESCE(rating, elo_rating, 1200)
            WHERE rating IS NULL
            """
        )
        cursor.execute("ALTER TABLE core_profile ALTER COLUMN rating SET DEFAULT 1200")
        cursor.execute(
            """
            UPDATE core_profile
            SET rating = 1200
            WHERE rating IS NULL
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0024_batchanalysisreport_share_token"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    fix_legacy_rating_column, migrations.RunPython.noop
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="profile",
                    name="legacy_rating",
                    field=models.IntegerField(db_column="rating", default=1200),
                ),
            ],
        ),
    ]
