import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0025_profile_legacy_rating_column"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserNotification",
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
                ("notification_type", models.CharField(db_index=True, max_length=40)),
                ("entity_id", models.CharField(db_index=True, max_length=128)),
                ("title", models.CharField(max_length=200)),
                ("body", models.TextField(blank=True, default="")),
                ("href", models.CharField(max_length=500)),
                ("meta", models.JSONField(blank=True, default=dict)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["user", "read_at", "-created_at"],
                        name="core_userno_user_id_6f0a0d_idx",
                    ),
                    models.Index(
                        fields=[
                            "user",
                            "notification_type",
                            "entity_id",
                            "-created_at",
                        ],
                        name="core_userno_user_id_8c2f1a_idx",
                    ),
                ],
            },
        ),
    ]
