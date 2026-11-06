from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from . import webpush
from .models import Notification, PushSubscription
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Notifications in-app de l'utilisateur connecté (« cloche » du tableau de bord)."""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"marked_read": updated})


class PushSubscriptionView(APIView):
    """Abonnement Web Push de l'appareil courant : clé publique VAPID (GET),
    enregistrement (POST) et désinscription (DELETE)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "enabled": webpush.is_configured(),
            "public_key": settings.WEBPUSH_VAPID_PUBLIC_KEY if webpush.is_configured() else "",
            "subscribed_devices": PushSubscription.objects.filter(user=request.user).count(),
        })

    def post(self, request):
        endpoint = request.data.get("endpoint")
        keys = request.data.get("keys") or {}
        if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
            return Response({"detail": "Abonnement push incomplet."}, status=status.HTTP_400_BAD_REQUEST)
        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": request.user, "p256dh": keys["p256dh"], "auth": keys["auth"],
                "user_agent": request.headers.get("User-Agent", "")[:300],
            },
        )
        return Response({"subscribed": True}, status=status.HTTP_201_CREATED)

    def delete(self, request):
        PushSubscription.objects.filter(user=request.user, endpoint=request.data.get("endpoint", "")).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
