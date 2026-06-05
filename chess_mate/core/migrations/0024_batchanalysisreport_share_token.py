from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_batchanalysisreport_credits"),
    ]

    operations = [
        migrations.AddField(
            model_name="batchanalysisreport",
            name="share_token",
            field=models.UUIDField(blank=True, db_index=True, null=True, unique=True),
        ),
    ]
