from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_game_date_played_default"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscription",
            name="tier",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="core.subscriptiontier"),
        ),
    ]
