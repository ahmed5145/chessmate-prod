from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013a_state_inject_payment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="amount",
            field=models.FloatField(default=0),
        ),
    ]
