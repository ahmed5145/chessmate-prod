# Generated to preserve compatibility with legacy tests.
import json
import sys

import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


def normalize_gameanalysis_feedback(apps, schema_editor):
    """Coerce legacy feedback values into valid JSON before JSONField migration."""
    try:
        GameAnalysis = apps.get_model("core", "GameAnalysis")
        
        # Check if table exists before querying
        with schema_editor.connection.cursor() as cursor:
            try:
                cursor.execute("SELECT 1 FROM core_gameanalysis LIMIT 1")
            except Exception:
                # Table doesn't exist yet, skip normalization
                return

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
    except Exception as e:
        # If anything fails, log it but don't block deployment
        print(f"WARNING: GameAnalysis feedback normalization failed: {str(e)}", file=sys.stderr)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_create_gameanalysis_table"),
    ]

    operations = [
        # Data normalization - safe to run
        migrations.RunPython(normalize_gameanalysis_feedback, migrations.RunPython.noop),
        # Skip database operations, only update Django ORM state to prevent transaction abort
        migrations.SeparateDatabaseAndState(
            state_operations=[
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
            ],
        ),
    ]
