"""
Views for batch analysis operations (PRD section 11, Step 9).
"""
import uuid
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import BatchAnalysisReport, Profile
from .serializers_batches import (
    BatchCreateSerializer,
    BatchStatusSerializer,
    BatchAnalysisReportSerializer,
)
from .tasks import analyze_batch_task


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def batch_create_view(request):
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
    serializer = BatchCreateSerializer(data=request.data, context={'request': request})
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract validated PGN list
    pgn_list = serializer.validated_data["pgn_list"]

    try:
        profile = Profile.objects.get(user=request.user)
        player_rating = profile.rating
    except Profile.DoesNotExist:
        player_rating = None
    
    # Generate batch_id as UUID string
    batch_id = str(uuid.uuid4())
    
    # Create BatchAnalysisReport with pending status
    batch_report = BatchAnalysisReport.objects.create(
        user=request.user,
        task_id=batch_id,
        status="pending",
        games_count=len(pgn_list),
    )
    
    # Queue the analysis task
    analyze_batch_task.delay(batch_id, pgn_list, request.user.id, player_rating=player_rating)
    
    return Response(
        {
            "batch_id": batch_report.pk,
            "task_id": batch_id,
            "status": "pending",
            "games_count": len(pgn_list),
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
        batch_report = BatchAnalysisReport.objects.get(
            id=batch_id, user=request.user
        )
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
        batch_report = BatchAnalysisReport.objects.get(
            id=batch_id, user=request.user
        )
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
        return Response(
            {
                "status": "failed",
                "message": "Analysis failed — insufficient games succeeded",
            },
            status=status.HTTP_200_OK,
        )
    
    # If analysis is completed or partial, return full report
    if batch_report.status in ["completed", "partial"]:
        serializer = BatchAnalysisReportSerializer(batch_report)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    # Fallback (should not reach here)
    return Response(
        {"detail": "Unknown batch status."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
