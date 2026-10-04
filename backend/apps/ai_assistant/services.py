import logging

from apps.equipment.models import Equipment
from apps.providers.models import Provider
from apps.venues.models import Venue

from .models import AssistantConversation, AssistantMessage
from .providers import AIProviderError, get_ai_provider

logger = logging.getLogger(__name__)


def build_catalog():
    return {
        "venues": list(Venue.objects.filter(is_active=True).values("id", "name", "capacity", "city")),
        "providers": list(Provider.objects.filter(is_active=True).values("id", "name", "category")),
        "equipment": list(Equipment.objects.filter(is_active=True).values("id", "name", "category")),
    }


def ask_assistant(user, conversation: AssistantConversation, prompt: str) -> AssistantMessage:
    AssistantMessage.objects.create(conversation=conversation, role=AssistantMessage.Role.USER, content=prompt)

    catalog = build_catalog()
    provider = get_ai_provider()
    try:
        result = provider.recommend(prompt, catalog)
    except AIProviderError:
        logger.exception("L'assistant IA n'a pas pu générer de réponse.")
        return AssistantMessage.objects.create(
            conversation=conversation,
            role=AssistantMessage.Role.ASSISTANT,
            content="Désolé, l'assistant est momentanément indisponible. Réessayez un peu plus tard.",
            recommendations={},
        )

    return AssistantMessage.objects.create(
        conversation=conversation,
        role=AssistantMessage.Role.ASSISTANT,
        content=result.get("message", ""),
        recommendations={
            "venues": result.get("venues", []),
            "providers": result.get("providers", []),
            "equipment": result.get("equipment", []),
        },
    )
