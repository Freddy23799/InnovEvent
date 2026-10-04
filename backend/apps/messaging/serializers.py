import mimetypes

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from rest_framework import serializers

from apps.documents.signing import sign_payload
from apps.documents.validators import validate_attachment_file

from .crypto import encrypt_bytes
from .models import Conversation, Message

User = get_user_model()

IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    body = serializers.CharField(required=False, allow_blank=True, default="")
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id", "conversation", "sender", "sender_name", "body", "is_read", "created_at",
            "attachment_url", "attachment_name", "attachment_content_type", "attachment_type", "attachment_size",
            "is_automated",
        ]
        read_only_fields = [
            "id", "sender", "is_read", "created_at",
            "attachment_url", "attachment_name", "attachment_content_type", "attachment_type", "attachment_size",
            "is_automated",
        ]

    def get_sender_name(self, obj):
        if obj.is_automated:
            return "Assistant InnovEvent"
        return obj.sender.get_full_name() or obj.sender.username

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return None
        # Signé et à courte durée de vie plutôt qu'une URL directe vers le
        # fichier (chiffré sur disque de toute façon) — un simple <img src>
        # ne peut pas porter d'en-tête d'authentification, donc l'accès passe
        # par un jeton dédié à ce message, vérifié dans MessageViewSet.attachment.
        token = sign_payload("message-attachment", obj.id)
        return f"/api/v1/messaging/messages/{obj.id}/attachment/?token={token}"

    def validate(self, attrs):
        request = self.context.get("request")
        upload = request.FILES.get("attachment") if request else None
        if not attrs.get("body", "").strip() and not upload:
            raise serializers.ValidationError("Un message doit contenir du texte ou une pièce jointe.")
        if upload:
            # La pièce jointe est chiffrée avant d'être écrite sur disque (voir
            # `create()`) : elle doit être validée ICI, sur le fichier original,
            # jamais après coup sur le blob chiffré (qui ne ressemble plus à
            # rien de reconnaissable — extension/signature perdues).
            try:
                validate_attachment_file(upload)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"attachment": exc.messages})
        return attrs

    def create(self, validated_data):
        body = validated_data.pop("body", "")
        request = self.context.get("request")
        upload = request.FILES.get("attachment") if request else None

        message = Message(**validated_data)
        message.body = body

        if upload:
            content_type = upload.content_type or mimetypes.guess_type(upload.name)[0] or "application/octet-stream"
            message.attachment_name = upload.name
            message.attachment_content_type = content_type
            message.attachment_size = upload.size
            message.attachment_type = Message.AttachmentType.IMAGE if content_type in IMAGE_TYPES else (
                Message.AttachmentType.AUDIO if content_type.startswith("audio/") else
                Message.AttachmentType.VIDEO if content_type.startswith("video/") else
                Message.AttachmentType.DOCUMENT if content_type == "application/pdf" or "document" in content_type or "text" in content_type else
                Message.AttachmentType.OTHER
            )
            encrypted = encrypt_bytes(upload.read())
            message.attachment.save(upload.name, ContentFile(encrypted), save=False)

        message.save()
        return message


class ConversationSerializer(serializers.ModelSerializer):
    participant_ids = serializers.PrimaryKeyRelatedField(
        source="participants", queryset=User.objects.all(), many=True, write_only=True
    )
    participants = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id", "participants", "participant_ids", "last_message", "unread_count",
            "is_admin_support", "human_handoff", "created_at",
        ]
        read_only_fields = ["id", "is_admin_support", "human_handoff", "created_at"]

    def get_participants(self, obj):
        return [
            {"id": u.id, "name": u.get_full_name() or u.username, "is_online": u.is_online()}
            for u in obj.participants.all()
        ]

    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        return MessageSerializer(last, context=self.context).data if last else None

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request:
            return 0
        return obj.unread_count_for(request.user)
