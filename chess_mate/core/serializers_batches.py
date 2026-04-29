"""
Serializers for batch analysis operations (PRD section 11).
"""
from rest_framework import serializers
from typing import List, Dict, Any
import chess.pgn
from io import StringIO

from .models import BatchAnalysisReport


class BatchCreateSerializer(serializers.Serializer):
    """
    Validates and processes a batch of games for analysis.
    
    Accepts either:
    - games: list of objects with 'pgn' string field
    - files: multipart file upload (converted to PGN strings)
    
    Validates batch size (5-30) and PGN parsability.
    Returns cleaned list of PGN strings.
    """

    games = serializers.ListField(
        child=serializers.CharField(),
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
        games = data.get("games", [])
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
                    raise serializers.ValidationError(
                        f"Failed to read uploaded file: {str(e)}"
                    )

        # Validate batch size
        batch_size = len(pgn_list)

        if batch_size < 5:
            raise serializers.ValidationError(
                "Batch analysis requires at least 5 games to detect patterns."
            )

        if batch_size > 30:
            raise serializers.ValidationError(
                "Batch analysis supports a maximum of 30 games."
            )

        # Validate each PGN is parseable
        validated_pgns = []
        for index, pgn_str in enumerate(pgn_list):
            try:
                # Attempt to parse the PGN using python-chess
                pgn_io = StringIO(pgn_str)
                game = chess.pgn.read_game(pgn_io)
                if game is None:
                    raise serializers.ValidationError(
                        f"Game at index {index}: Invalid or empty PGN."
                    )
                # Store the original PGN string (not parsed game)
                validated_pgns.append(pgn_str)
            except Exception as e:
                # Include index in error message
                raise serializers.ValidationError(
                    f"Game at index {index}: Failed to parse PGN: {str(e)}"
                )

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
    errors = serializers.SerializerMethodField()

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
        failed_list = obj.get("failed_games", [])
        errors = []
        if isinstance(failed_list, list):
            for item in failed_list:
                if isinstance(item, dict):
                    errors.append({
                        "game_id": item.get("game_id"),
                        "message": item.get("error", "Unknown error"),
                    })
        return errors


class BatchAnalysisReportSerializer(serializers.ModelSerializer):
    """
    Serializes a completed batch analysis report.
    Read-only.
    JSONFields (batch_summary, per_game_results, coaching_report) pass through as-is.
    """

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
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
