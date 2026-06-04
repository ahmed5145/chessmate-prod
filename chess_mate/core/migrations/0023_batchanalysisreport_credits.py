from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0022_games_legacy_columns"),
    ]

    operations = [
        migrations.AddField(
            model_name="batchanalysisreport",
            name="credits_charged",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="batchanalysisreport",
            name="credits_refunded",
            field=models.BooleanField(default=False),
        ),
    ]
