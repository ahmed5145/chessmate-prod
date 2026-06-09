"""API views for in-app notifications (SRG-14)."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .notifications import (
    get_notifications_payload,
    mark_all_notifications_read,
    mark_notification_read,
)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def notifications_view(request):
    """
    GET /api/v1/notifications/ — list notifications + unread count.
    PATCH — mark read: { "ids": [1, 2] } or { "mark_all": true }.
    """
    if request.method == "GET":
        return Response(get_notifications_payload(request.user), status=status.HTTP_200_OK)

    if request.data.get("mark_all"):
        updated = mark_all_notifications_read(request.user)
        payload = get_notifications_payload(request.user)
        payload["marked_read"] = updated
        return Response(payload, status=status.HTTP_200_OK)

    ids = request.data.get("ids") or []
    if not isinstance(ids, list):
        return Response(
            {"detail": "ids must be a list of notification ids."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    marked = 0
    for raw_id in ids:
        try:
            notification_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if mark_notification_read(request.user, notification_id):
            marked += 1

    payload = get_notifications_payload(request.user)
    payload["marked_read"] = marked
    return Response(payload, status=status.HTTP_200_OK)
