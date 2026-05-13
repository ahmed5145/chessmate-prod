from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013a_state_inject_payment"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS payments (
                id BIGSERIAL PRIMARY KEY,
                amount NUMERIC(10, 2) DEFAULT 0,
                credit_amount INTEGER DEFAULT 0,
                stripe_payment_id VARCHAR(100),
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id BIGINT REFERENCES auth_user(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS payments_user_id_idx ON payments(user_id);
            """,
            reverse_sql="DROP TABLE IF EXISTS payments CASCADE;",
        ),
        migrations.AlterField(
            model_name="payment",
            name="amount",
            field=models.FloatField(default=0),
        ),
    ]
