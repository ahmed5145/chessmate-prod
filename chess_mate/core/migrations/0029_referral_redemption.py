# Generated manually for SRG-24

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0028_spacedreminderlog"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="referral_code",
            field=models.CharField(
                blank=True, db_index=True, max_length=40, null=True, unique=True
            ),
        ),
        migrations.CreateModel(
            name="ReferralRedemption",
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
                ("referrer_credits", models.PositiveSmallIntegerField(default=5)),
                ("referee_credits", models.PositiveSmallIntegerField(default=5)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "batch_report",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="referral_redemptions",
                        to="core.batchanalysisreport",
                    ),
                ),
                (
                    "referee",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referral_redemption_received",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "referrer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referral_redemptions_given",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="referralredemption",
            index=models.Index(
                fields=["referrer", "-created_at"],
                name="core_referr_referre_91a2c1_idx",
            ),
        ),
    ]
