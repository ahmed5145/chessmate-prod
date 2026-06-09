"""Add Payment and AiFeedback to migration state only (renamed to follow chain).

This migration injects model state without executing any SQL so it can be
applied when the database is missing those tables. It depends on the
existing latest migration in the `core` app to keep the migration graph linear.
"""

import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_add_batchanalysisreport_status"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="AiFeedback",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("content", models.JSONField(default=dict)),
                        ("model_used", models.CharField(max_length=100)),
                        ("credits_used", models.IntegerField(default=0)),
                        ("created_at", models.DateTimeField(default=timezone.now)),
                        ("rating", models.IntegerField(blank=True, null=True)),
                        ("rating_comment", models.TextField(blank=True, null=True)),
                        (
                            "game",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                to="core.game",
                            ),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                to="auth.user",
                            ),
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
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "amount",
                            models.DecimalField(decimal_places=2, default=0, max_digits=10),
                        ),
                        ("credit_amount", models.IntegerField(default=0)),
                        (
                            "stripe_payment_id",
                            models.CharField(blank=True, max_length=100, null=True),
                        ),
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
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                to="auth.user",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "payments",
                        "ordering": ["-created_at"],
                    },
                ),
                migrations.AlterField(
                    model_name="gameanalysis",
                    name="feedback",
                    field=models.JSONField(default=dict, blank=True),
                ),
            ],
        ),
    ]
