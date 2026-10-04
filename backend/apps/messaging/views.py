from io import BytesIO

from django.contrib.auth import get_user_model
from django.http import FileResponse, Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.documents.signing import verify_payload
from apps.marketplace.feature_engine import resolve_features
from apps.marketplace.models import ProfessionalProfile
from apps.notifications.services import notify_new_message

from .crypto import decrypt_bytes
from .autoresponder import answer_support_message
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer

# Jetons d'accès aux pièces jointes valables 6 heures — assez pour couvrir une
# session de consultation de la messagerie, sans laisser un lien traîner
# indéfiniment dans un historique de navigateur.
ATTACHMENT_TOKEN_MAX_AGE = 6 * 60 * 60

User = get_user_model()


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user).prefetch_related("participants", "messages")

    def perform_create(self, serializer):
        conversation = serializer.save()
        conversation.participants.add(self.request.user)

    @action(detail=False, methods=["post"], url_path="contact-admin")
    def contact_admin(self, request):
        """Retrouve (ou crée) une conversation entre l'utilisateur courant et un
        administrateur, afin que tout client/participant/employé puisse joindre
        l'administration directement depuis la plateforme sans connaître son
        identifiant (la liste des comptes est réservée aux administrateurs)."""
        admin = User.objects.filter(role="admin", is_active=True).exclude(pk=request.user.pk).first()
        if not admin:
            return Response({"detail": "Aucun administrateur disponible pour le moment."}, status=status.HTTP_404_NOT_FOUND)

        conversation = Conversation.get_or_create_between(request.user, admin)
        if not conversation.is_admin_support:
            conversation.is_admin_support = True
            # Une conversation déjà reprise par un humain reste en suivi humain.
            conversation.human_handoff = conversation.messages.filter(sender=admin, is_automated=False).exists()
            conversation.save(update_fields=["is_admin_support", "human_handoff"])
        if not conversation.messages.exists():
            welcome = Message(conversation=conversation, sender=admin, is_automated=True, is_read=True)
            welcome.body = (
                f"Bonjour {request.user.first_name or request.user.username} ! Je suis l'assistant InnovEvent. "
                "Posez votre question sur une salle, une réservation, un devis, un paiement ou nos services. "
                "Je répondrai si possible; sinon l'administration prendra le relais dans cette conversation."
            )
            welcome.save()
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="contact-provider")
    def contact_provider(self, request):
        """Retrouve (ou crée) une conversation directe entre le client et le
        prestataire d'un profil professionnel — messagerie libre en complément
        des devis structurés, sans jamais échanger de coordonnées
        personnelles : tout passe par la plateforme. Piloté par le moteur de
        permissions comme le reste des fonctionnalités des marketplaces
        premium (clé « contact »)."""
        profile = ProfessionalProfile.objects.filter(pk=request.data.get("profile"), is_active=True).select_related("user").first()
        if not profile:
            return Response({"detail": "Profil professionnel introuvable."}, status=status.HTTP_404_NOT_FOUND)
        if profile.user_id == request.user.id:
            return Response({"detail": "Vous ne pouvez pas vous contacter vous-même."}, status=status.HTTP_400_BAD_REQUEST)

        if not request.user.is_admin_role:
            feature = next(
                (f for f in resolve_features(request.user, profile.marketplace_type) if f["key"] == "contact"), None
            )
            if not (feature and feature["visible"] and not feature["locked"]):
                raise PermissionDenied("Un abonnement actif à ce marketplace est requis pour contacter ce prestataire.")

        conversation = Conversation.get_or_create_between(request.user, profile.user)
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["conversation"]
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if self.action == "attachment":
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        return Message.objects.filter(conversation__participants=self.request.user).select_related("sender")

    @action(detail=True, methods=["get"])
    def attachment(self, request, pk=None):
        """Sert la pièce jointe déchiffrée à la volée — jamais exposée en
        clair sur le disque, et accessible uniquement via un jeton signé
        généré pour CE message précis (voir MessageSerializer.get_attachment_url),
        à durée de vie limitée. Un <img src> ne peut pas porter d'en-tête
        Authorization, d'où ce jeton plutôt qu'une vérification de session
        classique."""
        message = Message.objects.filter(pk=pk).select_related("conversation").first()
        if not message or not message.attachment:
            raise Http404("Pièce jointe introuvable.")

        token = request.query_params.get("token", "")
        verified_id = verify_payload(token, kind="message-attachment", max_age=ATTACHMENT_TOKEN_MAX_AGE)
        if verified_id is None or int(verified_id) != message.id:
            raise PermissionDenied("Lien de pièce jointe invalide ou expiré.")

        decrypted = decrypt_bytes(message.attachment.read())
        response = FileResponse(
            BytesIO(decrypted), content_type=message.attachment_content_type or "application/octet-stream",
        )
        disposition = "inline" if message.attachment_type == Message.AttachmentType.IMAGE else "attachment"
        response["Content-Disposition"] = f'{disposition}; filename="{message.attachment_name}"'
        return response

    def perform_create(self, serializer):
        conversation = serializer.validated_data["conversation"]
        if not conversation.participants.filter(pk=self.request.user.pk).exists():
            raise PermissionDenied("Vous ne participez pas à cette conversation.")
        message = serializer.save(sender=self.request.user)
        notify_new_message(message)

        if not conversation.is_admin_support:
            return

        if self.request.user.is_admin_role:
            if not conversation.human_handoff:
                conversation.human_handoff = True
                conversation.save(update_fields=["human_handoff"])
            return

        if conversation.human_handoff:
            return

        admin = conversation.participants.filter(role="admin", is_active=True).first()
        if not admin:
            return

        prior_messages = conversation.messages.exclude(pk=message.pk).select_related("sender").order_by("-created_at")
        history = [
            ("assistant" if prior.is_automated or prior.sender.is_admin_role else "user", prior.body)
            for prior in reversed(list(prior_messages[:24]))
        ]
        reply, handoff = answer_support_message(message.body, history=history)
        if handoff:
            conversation.human_handoff = True
            conversation.save(update_fields=["human_handoff"])

        automated_message = Message(
            conversation=conversation,
            sender=admin,
            is_automated=True,
            is_read=True,
        )
        automated_message.body = reply
        automated_message.save()

    @action(detail=False, methods=["post"], url_path="mark-read")
    def mark_read(self, request):
        conversation_id = request.data.get("conversation")
        updated = Message.objects.filter(
            conversation_id=conversation_id,
            conversation__participants=request.user,
        ).exclude(sender=request.user).update(is_read=True)
        return Response({"marked_read": updated})
