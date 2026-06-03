"""Sync core_profile columns on legacy production databases.

Older RDS schemas may have chesscom_username but not lichess_username, or be
missing other fields from 0001/0003/0004. Safe to re-run (IF NOT EXISTS / conditional rename).
"""

from django.db import migrations

SYNC_PROFILE_COLUMNS = """
-- Legacy rename from 0001 chesscom_username -> chess_com_username
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'core_profile'
          AND column_name = 'chesscom_username'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'core_profile'
          AND column_name = 'chess_com_username'
    ) THEN
        ALTER TABLE core_profile RENAME COLUMN chesscom_username TO chess_com_username;
    END IF;
END $$;

ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS lichess_username varchar(50) NOT NULL DEFAULT '';
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS chess_com_username varchar(50) NOT NULL DEFAULT '';
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS bio text NOT NULL DEFAULT '';
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS credits integer NOT NULL DEFAULT 10;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS email_verified boolean NOT NULL DEFAULT false;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS email_verification_token varchar(100) NULL;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS email_verification_sent_at timestamp with time zone NULL;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS email_verified_at timestamp with time zone NULL;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS last_credit_purchase timestamp with time zone NULL;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS preferences jsonb NOT NULL DEFAULT '{}';
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS rating_history jsonb NOT NULL DEFAULT '{}';
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS created_at timestamp with time zone NULL;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone NULL;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS elo_rating integer NOT NULL DEFAULT 1200;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS analysis_count integer NOT NULL DEFAULT 0;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS bullet_rating integer NOT NULL DEFAULT 1200;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS blitz_rating integer NOT NULL DEFAULT 1200;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS rapid_rating integer NOT NULL DEFAULT 1200;
ALTER TABLE core_profile ADD COLUMN IF NOT EXISTS classical_rating integer NOT NULL DEFAULT 1200;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_profile_rating_columns"),
    ]

    operations = [
        migrations.RunSQL(
            sql=SYNC_PROFILE_COLUMNS,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
