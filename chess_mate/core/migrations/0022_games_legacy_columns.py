"""Sync games table columns on legacy production databases.

RDS may predate 0001/0006/0007 or only partial migrations were applied. Dashboard and
batch analysis expect analysis_status and related fields. Safe to re-run.
"""

from django.db import migrations

SYNC_GAMES_COLUMNS = """
ALTER TABLE games ADD COLUMN IF NOT EXISTS game_url varchar(255) NULL;
ALTER TABLE games ADD COLUMN IF NOT EXISTS time_control_category varchar(20) NOT NULL DEFAULT 'blitz';
ALTER TABLE games ADD COLUMN IF NOT EXISTS opponent varchar(100) NOT NULL DEFAULT 'Unknown';
ALTER TABLE games ADD COLUMN IF NOT EXISTS opening_name varchar(200) NOT NULL DEFAULT 'Unknown Opening';
ALTER TABLE games ADD COLUMN IF NOT EXISTS time_control varchar(50) NOT NULL DEFAULT 'blitz';
ALTER TABLE games ADD COLUMN IF NOT EXISTS time_control_type varchar(20) NOT NULL DEFAULT 'blitz';
ALTER TABLE games ADD COLUMN IF NOT EXISTS eco_code varchar(3) NULL;
ALTER TABLE games ADD COLUMN IF NOT EXISTS opening_played varchar(200) NOT NULL DEFAULT 'Unknown Opening';
ALTER TABLE games ADD COLUMN IF NOT EXISTS opening_variation varchar(200) NOT NULL DEFAULT 'Unknown Variation';
ALTER TABLE games ADD COLUMN IF NOT EXISTS opponent_opening varchar(200) NOT NULL DEFAULT 'Unknown Opponent Opening';
ALTER TABLE games ADD COLUMN IF NOT EXISTS analysis_version integer NOT NULL DEFAULT 1;
ALTER TABLE games ADD COLUMN IF NOT EXISTS last_analysis_date timestamp with time zone NULL;
ALTER TABLE games ADD COLUMN IF NOT EXISTS analysis_status varchar(20) NOT NULL DEFAULT 'pending';
ALTER TABLE games ADD COLUMN IF NOT EXISTS analysis_priority integer NOT NULL DEFAULT 0;
ALTER TABLE games ADD COLUMN IF NOT EXISTS analysis jsonb NULL;
ALTER TABLE games ADD COLUMN IF NOT EXISTS feedback jsonb NULL;
ALTER TABLE games ADD COLUMN IF NOT EXISTS created_at timestamp with time zone NULL;
ALTER TABLE games ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone NULL;
ALTER TABLE games ADD COLUMN IF NOT EXISTS white_elo integer NULL;
ALTER TABLE games ADD COLUMN IF NOT EXISTS black_elo integer NULL;
ALTER TABLE games ADD COLUMN IF NOT EXISTS player_color varchar(5) NOT NULL DEFAULT 'white';
ALTER TABLE games ADD COLUMN IF NOT EXISTS status varchar(20) NOT NULL DEFAULT 'pending';
ALTER TABLE games ADD COLUMN IF NOT EXISTS analysis_completed_at timestamp with time zone NULL;

-- Align analysis_status with status for rows created before analysis_status existed
UPDATE games
SET analysis_status = status
WHERE status IS NOT NULL
  AND status <> ''
  AND analysis_status = 'pending'
  AND status <> 'pending';
"""


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0021_profile_legacy_columns"),
    ]

    operations = [
        migrations.RunSQL(
            sql=SYNC_GAMES_COLUMNS,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
