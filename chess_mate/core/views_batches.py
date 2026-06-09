"""
Views for batch analysis operations (PRD section 11, Step 9).
"""

import logging
import uuid

from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .abuse_limits import (
    batch_daily_limit_response,
    check_batch_creation_allowed,
    check_coaching_regenerate_allowed,
    coaching_regenerate_limit_response,
    record_coaching_regenerate,
)
from .batch_coaching import regenerate_batch_coaching
from .batch_compare import build_compare_narrative, metric_delta, weakness_themes
from .decorators import rate_limit
from .models import BatchAnalysisReport, Profile
from .priority_inbox import get_priority_inbox_payload, mark_priority_inbox_reviewed
from .serializers_batches import (
    BatchAnalysisReportSerializer,
    BatchCreateSerializer,
    BatchListItemSerializer,
    BatchPublicReportSerializer,
    BatchStatusSerializer,
)
from .tasks import analyze_batch_task

logger = logging.getLogger(__name__)


def _build_share_url(request, share_token) -> str:
    path = f"/share/batch/{share_token}"
    frontend_base = getattr(settings, "FRONTEND_URL", "").rstrip("/")
    if frontend_base:
        return f"{frontend_base}{path}"
    try:
        return request.build_absolute_uri(path)
    except Exception:
        return path


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def batch_inbox_view(request):
    """GET /api/v1/batches/inbox/ — pending coach priorities for the authenticated user."""
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        return Response(
            get_priority_inbox_payload(Profile(user=request.user)),
            status=status.HTTP_200_OK,
        )

    return Response(get_priority_inbox_payload(profile), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def batch_inbox_review_view(request):
    """POST /api/v1/batches/inbox/review/ — mark one priority item reviewed."""
    batch_id = request.data.get("batch_id")
    priority_index = request.data.get("priority_index")
    if batch_id is None or priority_index is None:
        return Response(
            {"detail": "batch_id and priority_index are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        batch_id_int = int(batch_id)
        priority_index_int = int(priority_index)
    except (TypeError, ValueError):
        return Response(
            {"detail": "Invalid batch_id or priority_index."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ok, message = mark_priority_inbox_reviewed(
        request.user,
        batch_id=batch_id_int,
        priority_index=priority_index_int,
    )
    if not ok:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in message.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        return Response({"detail": message}, status=status_code)

    try:
        profile = Profile.objects.get(user=request.user)
        inbox = get_priority_inbox_payload(profile)
    except Profile.DoesNotExist:
        inbox = get_priority_inbox_payload(Profile(user=request.user))

    return Response(
        {"detail": message, "priority_inbox": inbox}, status=status.HTTP_200_OK
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@rate_limit(endpoint_type="ANALYSIS")
def batch_collection_view(request):
    """GET /api/v1/batches/ — list history. POST — create a new batch job."""
    if request.method == "GET":
        return _batch_list_response(request)
    return _batch_create_response(request)


def _batch_list_response(request):
    """
    GET /api/v1/batches/?limit=20

    List the authenticated user's batch reports (newest first).
    """
    try:
        limit = int(request.query_params.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 50))

    queryset = BatchAnalysisReport.objects.filter(user=request.user).order_by(
        "-created_at"
    )[:limit]
    serializer = BatchListItemSerializer(queryset, many=True)
    return Response(
        {"results": serializer.data, "count": len(serializer.data)},
        status=status.HTTP_200_OK,
    )


def _batch_create_response(request):
    """
    POST /api/v1/batches/

    Create a new batch analysis job.

    Request:
        - games: list of PGN strings OR
        - files: multipart file upload

    Response (202):
        {
            "batch_id": <model id>,
            "task_id": <celery task id>,
            "status": "pending",
            "games_count": N
        }
    """
    serializer = BatchCreateSerializer(data=request.data, context={"request": request})

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Extract validated PGN list
    pgn_list = serializer.validated_data["pgn_list"]
    source_game_ids = serializer.validated_data.get("source_game_ids") or [None] * len(
        pgn_list
    )
    games_count = len(pgn_list)
    credits_per_game = int(getattr(settings, "BATCH_CREDITS_PER_GAME", 1))
    credits_required = games_count * credits_per_game

    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        return Response(
            {"detail": "User profile not found."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if credits_required > 0 and profile.credits < credits_required:
        return Response(
            {
                "detail": "Insufficient credits for this batch.",
                "required_credits": credits_required,
                "available_credits": profile.credits,
                "credits_per_game": credits_per_game,
            },
            status=status.HTTP_402_PAYMENT_REQUIRED,
        )

    batch_allowed, batch_limit_info = check_batch_creation_allowed(request.user)
    if not batch_allowed:
        return batch_daily_limit_response(batch_limit_info)

    # Generate batch_id as UUID string
    batch_id = str(uuid.uuid4())

    with transaction.atomic():
        if credits_required > 0:
            profile.credits -= credits_required
            profile.save(update_fields=["credits"])

        batch_report = BatchAnalysisReport.objects.create(
            user=request.user,
            task_id=batch_id,
            status="pending",
            games_count=games_count,
            game_ids=source_game_ids,
            credits_charged=credits_required,
        )

    # Queue the analysis task (requires Celery worker — see docker-entrypoint.sh)
    async_result = analyze_batch_task.delay(
        batch_id, pgn_list, request.user.id, source_game_ids
    )
    logger.info(
        "Queued batch %s (report id=%s) celery_id=%s games=%s user=%s",
        batch_id,
        batch_report.pk,
        async_result.id,
        games_count,
        request.user.id,
    )

    return Response(
        {
            "batch_id": batch_report.pk,
            "task_id": batch_id,
            "status": "pending",
            "games_count": games_count,
            "credits_charged": credits_required,
            "remaining_credits": profile.credits,
        },
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def batch_status_view(request, batch_id):
    """
    GET /api/v1/batches/{batch_id}/status/

    Retrieve the current status of a batch analysis.

    Response (200):
        {
            "batch_id": <model id>,
            "task_id": <celery task id>,
            "status": "pending|in_progress|completed|partial|failed",
            "games_count": N,
            "completed_games": <count>,
            "failed_games": <count>,
            "progress": "X/N games analyzed",
            "errors": [{"game_id": "...", "message": "..."}, ...]
        }
    """
    # Ownership check: batch must belong to request.user
    try:
        batch_report = BatchAnalysisReport.objects.get(id=batch_id, user=request.user)
    except BatchAnalysisReport.DoesNotExist:
        return Response(
            {"detail": "Batch not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Build dict from model instance for serializer
    batch_dict = {
        "id": batch_report.pk,
        "task_id": batch_report.task_id,
        "status": batch_report.status,
        "games_count": batch_report.games_count,
        "completed_games": batch_report.completed_games or [],
        "failed_games": batch_report.failed_games or [],
    }

    serializer = BatchStatusSerializer(batch_dict)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def batch_report_view(request, batch_id):
    """
    GET /api/v1/batches/{batch_id}/report/

    Retrieve the completed batch analysis report.

    Response:
        - 202 if status is "pending" or "in_progress"
        - 200 with full report if status is "completed" or "partial"
        - 200 with error message if status is "failed"
    """
    # Ownership check: batch must belong to request.user
    try:
        batch_report = BatchAnalysisReport.objects.get(id=batch_id, user=request.user)
    except BatchAnalysisReport.DoesNotExist:
        return Response(
            {"detail": "Batch not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # If analysis is still running, return 202
    if batch_report.status in ["pending", "in_progress"]:
        return Response(
            {
                "status": batch_report.status,
                "message": "Analysis in progress",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    # If analysis failed, return error message
    if batch_report.status == "failed":
        payload = {
            "status": "failed",
            "message": "Analysis failed — insufficient games succeeded",
            "credits_refunded": batch_report.credits_refunded,
        }
        if batch_report.credits_refunded and batch_report.credits_charged:
            payload["credits_refunded_amount"] = batch_report.credits_charged
        return Response(payload, status=status.HTTP_200_OK)

    # If analysis is completed or partial, return full report
    if batch_report.status in ["completed", "partial"]:
        serializer = BatchAnalysisReportSerializer(batch_report)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # Fallback (should not reach here)
    return Response(
        {"detail": "Unknown batch status."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@rate_limit(endpoint_type="BATCH_OPS")
def batch_regenerate_coaching_view(request, batch_id):
    """
    POST /api/v1/batches/{batch_id}/regenerate-coaching/

    Re-run OpenAI coaching from frozen batch_summary + per_game_results (no Stockfish).
    """
    try:
        batch_report = BatchAnalysisReport.objects.get(id=batch_id, user=request.user)
    except BatchAnalysisReport.DoesNotExist:
        return Response(
            {"detail": "Batch not found."}, status=status.HTTP_404_NOT_FOUND
        )

    if batch_report.status not in ("completed", "partial"):
        return Response(
            {"detail": "Batch Coach must finish before regenerating coaching."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    regen_allowed, regen_info = check_coaching_regenerate_allowed(
        request.user, batch_report.id
    )
    if not regen_allowed:
        return coaching_regenerate_limit_response(regen_info)

    ok, message = regenerate_batch_coaching(batch_report)
    if not ok:
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if "Insufficient" in message or "must finish" in message
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response({"detail": message}, status=status_code)

    record_coaching_regenerate(request.user, batch_report.id)

    serializer = BatchAnalysisReportSerializer(batch_report)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def batch_compare_view(request, batch_id):
    """
    GET /api/v1/batches/{batch_id}/compare/?other=<id|previous>

    Compare recurring weaknesses and headline metrics vs another batch.
    """
    try:
        current = BatchAnalysisReport.objects.get(id=batch_id, user=request.user)
    except BatchAnalysisReport.DoesNotExist:
        return Response(
            {"detail": "Batch not found."}, status=status.HTTP_404_NOT_FOUND
        )

    if current.status not in ("completed", "partial"):
        return Response(
            {"detail": "Current batch must be completed before comparing."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    other_param = request.query_params.get("other", "previous")
    if other_param == "previous":
        other = (
            BatchAnalysisReport.objects.filter(
                user=request.user,
                status__in=["completed", "partial"],
                pk__lt=current.pk,
            )
            .order_by("-pk")
            .first()
        )
        if not other:
            return Response(
                {"detail": "No earlier batch report to compare against."},
                status=status.HTTP_404_NOT_FOUND,
            )
    else:
        try:
            other_id = int(other_param)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid other batch id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            other = BatchAnalysisReport.objects.get(id=other_id, user=request.user)
        except BatchAnalysisReport.DoesNotExist:
            return Response(
                {"detail": "Comparison batch not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    if other.id == current.id:
        return Response(
            {"detail": "Choose a different batch to compare."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    current_summary = (
        current.batch_summary if isinstance(current.batch_summary, dict) else {}
    )
    other_summary = other.batch_summary if isinstance(other.batch_summary, dict) else {}

    current_themes = weakness_themes(current_summary)
    other_themes = weakness_themes(other_summary)

    metrics = {
        "overall_accuracy_pct_delta": metric_delta(
            current_summary, other_summary, "overall_accuracy_pct"
        ),
        "overall_eval_stability_delta": metric_delta(
            current_summary, other_summary, "overall_eval_stability"
        ),
    }
    weaknesses = {
        "persisting": sorted(current_themes & other_themes),
        "resolved": sorted(other_themes - current_themes),
        "new": sorted(current_themes - other_themes),
    }

    return Response(
        {
            "current_batch_id": current.id,
            "other_batch_id": other.id,
            "other_created_at": other.created_at,
            "metrics": metrics,
            "weaknesses": weaknesses,
            "narrative": build_compare_narrative(
                metrics=metrics,
                weaknesses=weaknesses,
                current_summary=current_summary,
                other_summary=other_summary,
            ),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def batch_share_view(request, batch_id):
    """
    POST /api/v1/batches/{batch_id}/share/ — enable link sharing.
    DELETE — revoke the public link.
    """
    try:
        batch_report = BatchAnalysisReport.objects.get(id=batch_id, user=request.user)
    except BatchAnalysisReport.DoesNotExist:
        return Response(
            {"detail": "Batch not found."}, status=status.HTTP_404_NOT_FOUND
        )

    if batch_report.status not in ("completed", "partial"):
        return Response(
            {"detail": "Only completed batch reports can be shared."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == "DELETE":
        batch_report.share_token = None
        batch_report.save(update_fields=["share_token", "updated_at"])
        return Response({"shared": False}, status=status.HTTP_200_OK)

    if not batch_report.share_token:
        batch_report.share_token = uuid.uuid4()
        batch_report.save(update_fields=["share_token", "updated_at"])

    share_url = _build_share_url(request, batch_report.share_token)
    return Response(
        {
            "shared": True,
            "share_token": str(batch_report.share_token),
            "share_url": share_url,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def batch_public_report_view(request, share_token):
    """
    GET /api/v1/batches/public/{share_token}/report/

    Anonymous read-only view of a shared batch report.
    """
    try:
        batch_report = BatchAnalysisReport.objects.get(
            share_token=share_token,
            status__in=["completed", "partial"],
        )
    except BatchAnalysisReport.DoesNotExist:
        return Response(
            {"detail": "Shared report not found."}, status=status.HTTP_404_NOT_FOUND
        )

    payload = BatchPublicReportSerializer.from_batch_report(batch_report)
    serializer = BatchPublicReportSerializer(payload)
    return Response(serializer.data, status=status.HTTP_200_OK)
