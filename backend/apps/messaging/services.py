"""Conversation de support (client ↔ administration) et messages de l'assistant."""

from apps.accounts.models import User

from .models import Conversation, Message

WELCOME_TEMPLATE = (
    "Bonjour {name} ! Je suis l'assistant InnovEvent. Posez votre question : "
    "je réponds tout de suite, et un conseiller prend le relais si besoin."
)


def get_support_conversation(user):
    """Retrouve (ou crée) la conversation de support de l'utilisateur.
    Retourne (conversation, admin) — (None, None) si aucun administrateur."""
    admin = User.objects.filter(role="admin", is_active=True).exclude(pk=user.pk).first()
    if not admin:
        return None, None
    conversation = Conversation.get_or_create_between(user, admin)
    if not conversation.is_admin_support:
        conversation.is_admin_support = True
        # Une conversation déjà reprise par un humain reste en suivi humain.
        conversation.human_handoff = conversation.messages.filter(sender=admin, is_automated=False).exists()
        conversation.save(update_fields=["is_admin_support", "human_handoff"])
    if not conversation.messages.exists():
        post_assistant_message(conversation, admin, WELCOME_TEMPLATE.format(name=user.first_name or user.username))
    return conversation, admin


def post_assistant_message(conversation, admin, body):
    message = Message(conversation=conversation, sender=admin, is_automated=True, is_read=True)
    message.body = body
    message.save()
    return message


def assistant_follow_up(user, body, title, link):
    """Relance de l'assistant : message dans la conversation de support du
    client + notification (temps réel et push) qui ouvre la bonne page."""
    from apps.notifications.services import notify_user

    conversation, admin = get_support_conversation(user)
    if conversation is not None:
        post_assistant_message(conversation, admin, body)
    notify_user(user, title=title, message=body[:300], link=link)
    return conversation
