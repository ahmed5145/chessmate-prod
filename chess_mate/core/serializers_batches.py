"""
Serializers for batch analysis operations (PRD section 11).
"""

from io import StringIO
from typing import Any, Dict, List

import chess.pgn
from django.conf import settings
from rest_framework import serializers

from .batch_labels import BATCH_COACH_MAX_GAMES, BATCH_COACH_REQUIRES_MIN
from .batch_moment_diff import build_batch_moment_diff
from .fix_rate import build_fix_rate_payload
from .models import BatchAnalysisReport, Game


def failed_games_to_errors(failed_list: List) -> List[Dict[str, Any]]:
    """Map stored failed_games JSON to API errors list (game_id + message)."""
    errors = []
    if not isinstance(failed_list, list):
        return errors
    for item in failed_list:
        if isinstance(item, dict):
            errors.append(
                {
                    "game_id": item.get("game_id"),
                    "message": item.get("error") or item.get("message") or "Unknown error",
                }
            )
    return errors


class BatchCreateSerializer(serializers.Serializer):
    """
    Validates and processes a batch of games for analysis.

    Accepts either:
    - games: list of PGN strings
    - game_ids: list of saved game IDs to resolve to PGNs
    - files: multipart file upload (converted to PGN strings)

    Validates batch size (5-30) and PGN parsability.
    Returns cleaned list of PGN strings.
    """

    games = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=False,
    )
    game_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=False,
    )
    files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=False,
    )

    def validate(self, data):
        """Validate batch size and PGN content."""
        request = self.context.get("request")
        games = data.get("games", [])
        game_ids = data.get("game_ids", [])
        files = data.get("files", [])

        # Collect PGN strings and parallel saved-game IDs (None for uploads/raw PGN).
        pgn_list = []
        source_game_ids: List[Any] = []

        # Process games field (list of PGN strings)
        if games:
            pgn_list.extend(games)
            source_game_ids.extend([None] * len(games))

        # Process files field (uploaded PGN files)
        if files:
            for file_obj in files:
                try:
                    content = file_obj.read()
                    if isinstance(content, bytes):
                        content = content.decode("utf-8")
                    pgn_list.append(content)
                    source_game_ids.append(None)
                except Exception as e:
                    raise serializers.ValidationError(f"Failed to read uploaded file: {str(e)}")

        # Resolve saved games to PGN strings when selected by ID.
        if game_ids:
            if request is None:
                raise serializers.ValidationError("Request context is required for game selection.")

            game_rows = list(Game.objects.filter(id__in=game_ids, user=request.user).values_list("id", "pgn"))
            if len(game_rows) != len(game_ids):
                raise serializers.ValidationError("One or more game IDs are invalid or do not belong to you.")

            games_by_id = {game_id: pgn for game_id, pgn in game_rows}
            try:
                for game_id in game_ids:
                    pgn_list.append(games_by_id[game_id])
                    source_game_ids.append(game_id)
            except KeyError as exc:
                raise serializers.ValidationError("One or more game IDs are invalid or do not belong to you.") from exc

        # Validate batch size
        batch_size = len(pgn_list)

        min_games = int(getattr(settings, "BATCH_MIN_GAMES", 5))
        max_games = int(getattr(settings, "BATCH_MAX_GAMES", 30))

        if batch_size < min_games:
            raise serializers.ValidationError(BATCH_COACH_REQUIRES_MIN.format(min_games=min_games))

        if batch_size > max_games:
            raise serializers.ValidationError(BATCH_COACH_MAX_GAMES.format(max_games=max_games))

        # Validate each PGN is parseable
        validated_pgns = []
        for index, pgn_str in enumerate(pgn_list):
            try:
                # Attempt to parse the PGN using python-chess
                pgn_io = StringIO(pgn_str)
                game = chess.pgn.read_game(pgn_io)
                if game is None:
                    raise serializers.ValidationError(f"Game at index {index}: Invalid or empty PGN.")
                # Store the original PGN string (not parsed game)
                validated_pgns.append(pgn_str)
            except Exception as e:
                # Include index in error message
                raise serializers.ValidationError(f"Game at index {index}: Failed to parse PGN: {str(e)}")

        data["pgn_list"] = validated_pgns
        data["source_game_ids"] = source_game_ids[: len(validated_pgns)]
        return data

    def to_representation(self, instance):
        """Return the cleaned PGN list."""
        return {"pgn_list": instance.get("pgn_list", [])}


class BatchStatusSerializer(serializers.Serializer):
    """
    Serializes the status of a batch analysis task.
    Read-only.
    """

    batch_id = serializers.SerializerMethodField()
    task_id = serializers.CharField()
    status = serializers.CharField()
    games_count = serializers.IntegerField()
    completed_games = serializers.SerializerMethodField()
    failed_games = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    def get_batch_id(self, obj):
        """Map id to batch_id."""
        return obj.get("id") or obj.get("batch_id")

    def get_completed_games(self, obj):
        """Count of completed games (integer)."""
        completed_list = obj.get("completed_games", [])
        if isinstance(completed_list, list):
            return len(completed_list)
        return 0

    def get_failed_games(self, obj):
        """Count of failed games (integer)."""
        failed_list = obj.get("failed_games", [])
        if isinstance(failed_list, list):
            return len(failed_list)
        return 0

    def get_progress(self, obj):
        """Generate progress string e.g. '8/15 games analyzed'."""
        games_count = obj.get("games_count", 0)
        completed = self.get_completed_games(obj)
        return f"{completed}/{games_count} games analyzed"

    def get_errors(self, obj):
        """Extract error list from failed_games."""
        return failed_games_to_errors(obj.get("failed_games", []))

    def to_representation(self, instance):
        """Return the batch status payload expected by the frontend."""
        completed_list = instance.get("completed_games", [])
        failed_list = instance.get("failed_games", [])
        completed_games = len(completed_list) if isinstance(completed_list, list) else 0
        failed_games = len(failed_list) if isinstance(failed_list, list) else 0
        errors = failed_games_to_errors(failed_list)

        games_count = instance.get("games_count", 0)
        batch_id = instance.get("id") or instance.get("batch_id")

        return {
            "batch_id": batch_id,
            "task_id": instance.get("task_id"),
            "status": instance.get("status"),
            "games_count": games_count,
            "completed_games": completed_games,
            "failed_games": failed_games,
            "progress": f"{completed_games}/{games_count} games analyzed",
            "errors": errors,
        }


def _coaching_summary_snippet(coaching_report: Any, max_len: int = 200) -> str:
    """One-line preview from coaching_report for list/history views."""
    if not isinstance(coaching_report, dict):
        return ""
    raw = coaching_report.get("executive_summary") or coaching_report.get("summary") or ""
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    text = str(raw).strip()
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 1].rstrip()}…"


class BatchListItemSerializer(serializers.ModelSerializer):
    """Lightweight batch row for history lists."""

    coach_summary = serializers.SerializerMethodField()
    overall_accuracy_pct = serializers.SerializerMethodField()

    class Meta:
        model = BatchAnalysisReport
        fields = [
            "id",
            "status",
            "games_count",
            "coach_summary",
            "overall_accuracy_pct",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_coach_summary(self, obj: BatchAnalysisReport) -> str:
        return _coaching_summary_snippet(obj.coaching_report)

    def get_overall_accuracy_pct(self, obj: BatchAnalysisReport):
        summary = obj.batch_summary if isinstance(obj.batch_summary, dict) else {}
        return summary.get("overall_accuracy_pct")


def sanitize_per_game_results_for_public(
    per_game_results: List[Dict[str, Any]] | None,
) -> List[Dict[str, Any]]:
    """Strip private links/ids from per-game payloads for anonymous viewers."""
    if not isinstance(per_game_results, list):
        return []
    sanitized = []
    for game in per_game_results:
        if not isinstance(game, dict):
            continue
        row = dict(game)
        row.pop("saved_game_id", None)
        sanitized.append(row)
    return sanitized


class BatchPublicReportSerializer(serializers.Serializer):
    """Read-only public batch report (no auth)."""

    status = serializers.CharField()
    games_count = serializers.IntegerField()
    batch_summary = serializers.JSONField()
    per_game_results = serializers.JSONField()
    coaching_report = serializers.JSONField(allow_null=True)
    created_at = serializers.DateTimeField()

    @classmethod
    def from_batch_report(cls, batch_report: BatchAnalysisReport) -> Dict[str, Any]:
        return {
            "status": batch_report.status,
            "games_count": batch_report.games_count,
            "batch_summary": batch_report.batch_summary or {},
            "per_game_results": sanitize_per_game_results_for_public(batch_report.per_game_results),
            "coaching_report": batch_report.coaching_report,
            "created_at": batch_report.created_at,
        }


class BatchAnalysisReportSerializer(serializers.ModelSerializer):
    """
    Serializes a completed batch analysis report.
    Read-only.
    JSONFields (batch_summary, per_game_results, coaching_report) pass through as-is.
    """

    errors = serializers.SerializerMethodField()

    class Meta:
        model = BatchAnalysisReport
        fields = [
            "id",
            "task_id",
            "status",
            "games_count",
            "batch_summary",
            "per_game_results",
            "coaching_report",
            "failed_games",
            "errors",
            "share_token",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_errors(self, obj: BatchAnalysisReport) -> List[Dict[str, Any]]:
        return failed_games_to_errors(obj.failed_games or [])

    def to_representation(self, instance: BatchAnalysisReport) -> Dict[str, Any]:
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request and getattr(request, "user", None):
            profile = getattr(request.user, "profile", None)
            if profile is not None:
                from .moment_timeline import enrich_batch_report_payload

                data = enrich_batch_report_payload(data, profile)

            previous = (
                BatchAnalysisReport.objects.filter(
                    user=request.user,
                    status__in=["completed", "partial"],
                    pk__lt=instance.pk,
                )
                .order_by("-pk")
                .first()
            )
            if previous:
                data["fix_rate"] = build_fix_rate_payload(instance, previous)
                data["moment_diff"] = build_batch_moment_diff(
                    instance, previous, profile
                )
            else:
                data["fix_rate"] = {"show": False}
                data["moment_diff"] = {"show": False}
        return data
