from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_gameanalysis_depth_field"),
    ]

    operations = [
        migrations.CreateModel(
            name="BatchAnalysisReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("task_id", models.CharField(db_index=True, max_length=255)),
                ("game_ids", models.JSONField(blank=True, default=list)),
                ("games_count", models.IntegerField(default=0)),
                ("completed_games", models.JSONField(blank=True, default=list)),
                ("failed_games", models.JSONField(blank=True, default=list)),
                ("aggregate_metrics", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="batch_analysis_reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Batch Analysis Report",
                "verbose_name_plural": "Batch Analysis Reports",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="batchanalysisreport",
            index=models.Index(fields=["user", "created_at"], name="core_batcha_user_id_ae6e17_idx"),
        ),
        migrations.AddIndex(
            model_name="batchanalysisreport",
            index=models.Index(fields=["task_id"], name="core_batcha_task_id_dd8906_idx"),
        ),
        migrations.AddConstraint(
            model_name="batchanalysisreport",
            constraint=models.UniqueConstraint(fields=("user", "task_id"), name="unique_user_batch_report_task"),
        ),
    ]
