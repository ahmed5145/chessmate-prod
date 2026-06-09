import json

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html

from .batch_coaching import regenerate_batch_coaching
from .batch_rerun import BatchRerunError, queue_batch_rerun
from .models import (
    BatchAnalysisReport,
    Game,
    GameAnalysis,
    Player,
    Profile,
    Transaction,
)


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "date_joined",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("-date_joined",)


admin.site.site_header = "ChessMate Operations"
admin.site.site_title = "ChessMate Admin"
admin.site.index_title = "Site administration"

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("username", "date_joined")
    search_fields = ("username",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "credits",
        "bullet_rating",
        "blitz_rating",
        "rapid_rating",
        "classical_rating",
        "total_games",
        "win_rate",
    )
    search_fields = ("user__username", "user__email")
    list_filter = ("bullet_rating", "blitz_rating", "rapid_rating", "classical_rating")
    readonly_fields = ("win_rate",)
    actions = ("grant_10_credits", "grant_50_credits", "grant_100_credits")

    @admin.action(description="Grant 10 credits")
    def grant_10_credits(self, request, queryset):
        self._grant_credits(request, queryset, 10)

    @admin.action(description="Grant 50 credits")
    def grant_50_credits(self, request, queryset):
        self._grant_credits(request, queryset, 50)

    @admin.action(description="Grant 100 credits")
    def grant_100_credits(self, request, queryset):
        self._grant_credits(request, queryset, 100)

    def _grant_credits(self, request, queryset, amount: int) -> None:
        updated = 0
        for profile in queryset:
            profile.credits = (profile.credits or 0) + amount
            profile.save(update_fields=["credits"])
            updated += 1
        self.message_user(
            request,
            f"Granted {amount} credits to {updated} profile(s).",
            messages.SUCCESS,
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "preferences" in form.base_fields:
            form.base_fields["preferences"].initial = {
                "theme": "light",
                "email_notifications": True,
                "analysis_depth": 20,
            }
        if "rating_history" in form.base_fields:
            form.base_fields["rating_history"].initial = {
                "bullet": [],
                "blitz": [],
                "rapid": [],
                "classical": [],
            }
        return form

    def save_model(self, request, obj, form, change):
        if not obj.preferences:
            obj.preferences = {}
        if not obj.rating_history:
            obj.rating_history = {
                "bullet": [],
                "blitz": [],
                "rapid": [],
                "classical": [],
            }
        super().save_model(request, obj, form, change)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "white",
        "black",
        "result",
        "platform",
        "date_played",
        "opening_name",
    )
    list_filter = ("platform", "result", "date_played")
    search_fields = ("white", "black", "user__username", "opening_name")
    ordering = ("-date_played",)
    raw_id_fields = ("user",)


@admin.register(GameAnalysis)
class GameAnalysisAdmin(admin.ModelAdmin):
    list_display = ("id", "game", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("game__white", "game__black", "game__user__username")
    ordering = ("-created_at",)
    raw_id_fields = ("game",)


@admin.register(BatchAnalysisReport)
class BatchAnalysisReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "status",
        "games_count",
        "failed_count",
        "has_coaching",
        "credits_charged",
        "created_at",
    )
    list_filter = ("status", "created_at", "credits_refunded")
    search_fields = ("task_id", "user__username", "user__email")
    ordering = ("-created_at",)
    raw_id_fields = ("user",)
    readonly_fields = (
        "created_at",
        "updated_at",
        "report_link",
        "failed_games_display",
        "coach_summary_preview",
    )
    actions = ("regenerate_coaching", "rerun_stockfish_analysis")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "task_id",
                    "status",
                    "games_count",
                    "credits_charged",
                    "credits_refunded",
                    "share_token",
                    "report_link",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Failures",
            {"fields": ("failed_games_display",), "classes": ("collapse",)},
        ),
        (
            "Coaching preview",
            {"fields": ("coach_summary_preview",), "classes": ("collapse",)},
        ),
        (
            "Raw payloads",
            {
                "fields": (
                    "game_ids",
                    "completed_games",
                    "failed_games",
                    "aggregate_metrics",
                    "batch_summary",
                    "per_game_results",
                    "coaching_report",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Failed")
    def failed_count(self, obj: BatchAnalysisReport) -> int:
        failed = obj.failed_games or []
        return len(failed) if isinstance(failed, list) else 0

    @admin.display(boolean=True, description="Coaching")
    def has_coaching(self, obj: BatchAnalysisReport) -> bool:
        return bool(obj.coaching_report)

    @admin.display(description="Report URL")
    def report_link(self, obj: BatchAnalysisReport) -> str:
        if not obj.id:
            return "—"
        return format_html(
            '<a href="/batch-report/{}" target="_blank" rel="noopener">/batch-report/{}</a>',
            obj.id,
            obj.id,
        )

    @admin.display(description="Failed games")
    def failed_games_display(self, obj: BatchAnalysisReport) -> str:
        failed = obj.failed_games or []
        if not failed:
            return "None"
        try:
            return format_html("<pre>{}</pre>", json.dumps(failed, indent=2))
        except (TypeError, ValueError):
            return str(failed)

    @admin.display(description="Coach summary")
    def coach_summary_preview(self, obj: BatchAnalysisReport) -> str:
        coaching = obj.coaching_report or {}
        summary = coaching.get("executive_summary") or coaching.get("summary") or ""
        if not summary:
            return "No coaching report"
        text = str(summary)
        if len(text) > 500:
            text = f"{text[:500]}…"
        return text

    @admin.action(
        description="Re-run Stockfish analysis (classification fixes, no credits)"
    )
    def rerun_stockfish_analysis(self, request, queryset):
        ok_count = 0
        for batch_report in queryset:
            try:
                message = queue_batch_rerun(batch_report)
                ok_count += 1
                self.message_user(request, message, messages.SUCCESS)
            except BatchRerunError as exc:
                self.message_user(
                    request,
                    f"Batch {batch_report.id}: {exc}",
                    messages.ERROR,
                )
        if ok_count:
            self.message_user(
                request,
                f"Queued Stockfish re-analysis for {ok_count} batch report(s).",
                messages.SUCCESS,
            )

    @admin.action(description="Regenerate coaching (OpenAI, no Stockfish)")
    def regenerate_coaching(self, request, queryset):
        ok_count = 0
        for batch_report in queryset:
            ok, message = regenerate_batch_coaching(batch_report)
            if ok:
                ok_count += 1
            else:
                self.message_user(
                    request,
                    f"Batch {batch_report.id}: {message}",
                    messages.ERROR,
                )
        if ok_count:
            self.message_user(
                request,
                f"Regenerated coaching for {ok_count} batch report(s).",
                messages.SUCCESS,
            )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "transaction_type", "credits", "status", "created_at")
    list_filter = ("transaction_type", "status", "created_at")
    search_fields = ("user__username", "stripe_payment_id")
    ordering = ("-created_at",)
    raw_id_fields = ("user",)
