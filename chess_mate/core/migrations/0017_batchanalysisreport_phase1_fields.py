# Generated migration for Phase 1 batch analysis fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_batchanalysisreport"),
    ]

    operations = [
        migrations.AddField(
            model_name="batchanalysisreport",
            name="batch_summary",
            field=models.JSONField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="batchanalysisreport",
            name="per_game_results",
            field=models.JSONField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="batchanalysisreport",
            name="coaching_report",
            field=models.JSONField(blank=True, default=None, null=True),
        ),
    ]
