from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_profile_compat_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="game",
            name="date_played",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
