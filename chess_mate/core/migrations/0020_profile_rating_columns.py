"""Add Profile rating columns missing on older production databases.

RDS was created before 0001_initial's full Profile shape (or only 0011 fields were applied).
Uses IF NOT EXISTS so it is safe on databases that already have these columns.
"""

from django.db import migrations

ADD_PROFILE_RATING_COLUMNS = """
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS bullet_rating integer NOT NULL DEFAULT 1200;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS blitz_rating integer NOT NULL DEFAULT 1200;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS rapid_rating integer NOT NULL DEFAULT 1200;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS classical_rating integer NOT NULL DEFAULT 1200;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0019_state_only_models"),
    ]

    operations = [
        migrations.RunSQL(
            sql=ADD_PROFILE_RATING_COLUMNS,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
