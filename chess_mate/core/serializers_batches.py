"""
Serializers for batch analysis operations (PRD section 11).
"""

from io import StringIO
from typing import Any, Dict, List

import chess.pgn
from django.conf import settings
from rest_framework import serializers

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

        # Collect PGN strings from both sources
        pgn_list = []

        # Process games field (list of PGN strings)
        if games:
            pgn_list.extend(games)

        # Process files field (uploaded PGN files)
        if files:
            for file_obj in files:
                try:
                    content = file_obj.read()
                    if isinstance(content, bytes):
                        content = content.decode("utf-8")
                    pgn_list.append(content)
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
                pgn_list.extend(games_by_id[game_id] for game_id in game_ids)
            except KeyError as exc:
                raise serializers.ValidationError("One or more game IDs are invalid or do not belong to you.") from exc

        # Validate batch size
        batch_size = len(pgn_list)

        min_games = int(getattr(settings, "BATCH_MIN_GAMES", 5))
        max_games = int(getattr(settings, "BATCH_MAX_GAMES", 30))

        if batch_size < min_games:
            raise serializers.ValidationError(
                f"Batch analysis requires at least {min_games} games to detect patterns."
            )

        if batch_size > max_games:
            raise serializers.ValidationError(
                f"Batch analysis supports a maximum of {max_games} games."
            )

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
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_errors(self, obj: BatchAnalysisReport) -> List[Dict[str, Any]]:
        return failed_games_to_errors(obj.failed_games or [])
