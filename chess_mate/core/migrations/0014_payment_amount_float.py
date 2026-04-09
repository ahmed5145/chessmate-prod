from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_subscription_tier_nullable"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="amount",
            field=models.FloatField(default=0),
        ),
    ]
