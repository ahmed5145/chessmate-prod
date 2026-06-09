# Generated manually for SRG-15

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0026_usernotification"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailSendLog",
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
                ("email_type", models.CharField(db_index=True, max_length=40)),
                (
                    "week_key",
                    models.CharField(
                        blank=True, db_index=True, default="", max_length=16
                    ),
                ),
                ("sent_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("meta", models.JSONField(blank=True, default=dict)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_send_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-sent_at"],
            },
        ),
        migrations.AddIndex(
            model_name="emailsendlog",
            index=models.Index(
                fields=["user", "email_type", "week_key"],
                name="core_emails_user_id_6e0f2a_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="emailsendlog",
            index=models.Index(
                fields=["user", "email_type", "-sent_at"],
                name="core_emails_user_id_8b41c1_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="emailsendlog",
            constraint=models.UniqueConstraint(
                fields=("user", "email_type", "week_key"),
                name="unique_user_email_type_week",
            ),
        ),
    ]
