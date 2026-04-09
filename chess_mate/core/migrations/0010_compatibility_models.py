# Generated to preserve compatibility with legacy tests.
import json

import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


def normalize_gameanalysis_feedback(apps, schema_editor):
    """Coerce legacy feedback values into valid JSON before JSONField migration."""
    GameAnalysis = apps.get_model("core", "GameAnalysis")

    for analysis in GameAnalysis.objects.all().iterator():
        value = analysis.feedback
        normalized = value

        if value is None:
            normalized = {}
        elif isinstance(value, str):
            text = value.strip()
            if not text:
                normalized = {}
            else:
                try:
                    normalized = json.loads(text)
                except json.JSONDecodeError:
                    normalized = {"legacy_feedback": text}
        elif not isinstance(value, (dict, list, int, float, bool)):
            normalized = {"legacy_feedback": str(value)}

        if normalized != value:
            analysis.feedback = normalized
            analysis.save(update_fields=["feedback"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_create_gameanalysis_table"),
    ]

    operations = [
        migrations.RunPython(normalize_gameanalysis_feedback, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="gameanalysis",
            name="feedback",
            field=models.JSONField(default=dict, blank=True),
        ),
        migrations.CreateModel(
            name="AiFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.JSONField(default=dict)),
                ("model_used", models.CharField(max_length=100)),
                ("credits_used", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(default=timezone.now)),
                ("rating", models.IntegerField(blank=True, null=True)),
                ("rating_comment", models.TextField(blank=True, null=True)),
                (
                    "game",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.game"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="auth.user"),
                ),
            ],
            options={
                "db_table": "ai_feedback",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("credit_amount", models.IntegerField(default=0)),
                ("stripe_payment_id", models.CharField(blank=True, max_length=100, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("refunded", "Refunded"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(default=timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="auth.user"),
                ),
            ],
            options={
                "db_table": "payments",
                "ordering": ["-created_at"],
            },
        ),
    ]
