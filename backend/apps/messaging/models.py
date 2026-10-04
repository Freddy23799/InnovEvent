from django.conf import settings
from django.db import models

from .crypto import decrypt_text, encrypt_text


class Conversation(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
    is_admin_support = models.BooleanField(default=False)
    human_handoff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Conversation #{self.pk}"

    def unread_count_for(self, user):
        return self.messages.exclude(sender=user).filter(is_read=False).count()

    @classmethod
    def get_or_create_between(cls, user_a, user_b):
        """Retrouve (ou crée) l'unique conversation directe entre deux comptes —
        partagé par toutes les mises en relation de la plateforme (contact
        admin, contact prestataire, mise en relation manuelle sur une demande)
        pour ne jamais dupliquer un fil de discussion existant."""
        conversation = cls.objects.filter(participants=user_a).filter(participants=user_b).first()
        if not conversation:
            conversation = cls.objects.create()
            conversation.participants.add(user_a, user_b)
        return conversation


class Message(models.Model):
    class AttachmentType(models.TextChoices):
        IMAGE = "image", "Image"
        DOCUMENT = "document", "Document"
        AUDIO = "audio", "Audio"
        VIDEO = "video", "Vidéo"
        OTHER = "other", "Autre"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    # Stocke le texte CHIFFRÉ (Fernet) — jamais en clair en base. Accès en
    # clair uniquement via la propriété Python `body` ci-dessous.
    body_encrypted = models.TextField(blank=True)

    # Pièce jointe : les octets stockés sur le disque sont eux aussi chiffrés
    # (voir apps.messaging.crypto) — un accès direct au volume de stockage ne
    # suffit pas à ouvrir le fichier. Le déchiffrement n'a lieu qu'à la volée,
    # via l'action `attachment` du ViewSet, réservée aux participants de la
    # conversation.
    attachment = models.FileField(upload_to="messaging/attachments/%Y/%m/", blank=True, null=True)
    attachment_name = models.CharField(max_length=255, blank=True, help_text="Nom de fichier d'origine")
    attachment_content_type = models.CharField(max_length=100, blank=True)
    attachment_type = models.CharField(max_length=10, choices=AttachmentType.choices, blank=True)
    attachment_size = models.PositiveIntegerField(null=True, blank=True, help_text="Taille d'origine en octets")
    is_automated = models.BooleanField(default=False)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender} — {self.body[:30] if self.body_encrypted else (self.attachment_name or 'pièce jointe')}"

    @property
    def body(self):
        return decrypt_text(self.body_encrypted)

    @body.setter
    def body(self, value):
        self.body_encrypted = encrypt_text(value or "")
