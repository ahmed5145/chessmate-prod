from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_compatibility_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="elo_rating",
            field=models.IntegerField(default=1200),
        ),
        migrations.AddField(
            model_name="profile",
            name="analysis_count",
            field=models.IntegerField(default=0),
        ),
    ]
