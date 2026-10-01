"""Architecture de fournisseur IA interchangeable (section 12 du CDC).

`DemoAIProvider` est pleinement fonctionnel hors ligne : il ne recommande que des
ressources réellement présentes et actives en base (aucune invention). `LLMProvider`
appelle une API compatible OpenAI (chat completions) pour reformuler la réponse et
affiner le choix parmi les MÊMES ressources fournies en contexte — le modèle ne
reçoit jamais la permission d'inventer un identifiant hors de cette liste.

Changer de fournisseur = changer `AI_PROVIDER` dans l'environnement, sans toucher
au reste du code métier (views.py, models.py restent identiques).
"""

import json
from abc import ABC, abstractmethod

import requests
from django.conf import settings


class AIProviderError(Exception):
    pass


class BaseAIProvider(ABC):
    @abstractmethod
    def recommend(self, prompt: str, catalog: dict) -> dict:
        """`catalog` contient les listes de ressources actives disponibles :
        {"venues": [...], "providers": [...], "equipment": [...]}.
        Doit renvoyer {"message": str, "venues": [id...], "providers": [id...], "equipment": [id...]}.
        """
        raise NotImplementedError


class DemoAIProvider(BaseAIProvider):
    KEYWORDS = {
        "dj": "dj",
        "musique": "dj",
        "son": "dj",
        "traiteur": "caterer",
        "repas": "caterer",
        "nourriture": "caterer",
        "decoration": "decoration",
        "décoration": "decoration",
        "securite": "security",
        "sécurité": "security",
        "photo": "photography",
    }

    def recommend(self, prompt, catalog):
        prompt_lower = prompt.lower()
        wanted_categories = {cat for kw, cat in self.KEYWORDS.items() if kw in prompt_lower}

        venues = catalog["venues"]
        providers = catalog["providers"]
        equipment = catalog["equipment"]

        if wanted_categories:
            providers = [p for p in providers if p["category"] in wanted_categories]

        recommended_venues = sorted(venues, key=lambda v: v["capacity"])[:3]
        recommended_providers = providers[:3]
        recommended_equipment = equipment[:5]

        parts = ["Voici mes recommandations basées sur les ressources actuellement disponibles :"]
        if recommended_venues:
            parts.append("Salles : " + ", ".join(f"{v['name']} (capacité {v['capacity']})" for v in recommended_venues))
        else:
            parts.append("Aucune salle disponible ne correspond à votre demande pour le moment.")
        if recommended_providers:
            parts.append("Prestataires : " + ", ".join(p["name"] for p in recommended_providers))
        if recommended_equipment:
            parts.append("Matériel suggéré : " + ", ".join(e["name"] for e in recommended_equipment))

        return {
            "message": "\n".join(parts),
            "venues": [v["id"] for v in recommended_venues],
            "providers": [p["id"] for p in recommended_providers],
            "equipment": [e["id"] for e in recommended_equipment],
        }


class LLMProvider(BaseAIProvider):
    """Passerelle vers une API de complétion de chat compatible OpenAI.

    Fonctionne avec tout fournisseur exposant le même contrat d'API
    (endpoint /chat/completions, réponse `choices[0].message.content`) en
    changeant simplement `AI_PROVIDER_BASE_URL` et `AI_PROVIDER_API_KEY`.
    """

    def __init__(self):
        self.api_key = settings.AI_PROVIDER_API_KEY
        self.base_url = getattr(settings, "AI_PROVIDER_BASE_URL", "https://api.openai.com/v1")
        self.model = getattr(settings, "AI_PROVIDER_MODEL", "gpt-4o-mini")

    def recommend(self, prompt, catalog):
        if not self.api_key:
            raise AIProviderError("Aucune clé API IA configurée (AI_PROVIDER_API_KEY manquant).")

        system_prompt = (
            "Tu es l'assistant InnovEvent-GS. Tu dois choisir exclusivement parmi les ressources "
            "listées ci-dessous (par leur id). N'invente jamais de ressource. "
            "Réponds uniquement en JSON avec les clés message, venues, providers, equipment "
            "(listes d'ids). Catalogue disponible : " + json.dumps(catalog, ensure_ascii=False)
        )
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                },
                timeout=15,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except (requests.RequestException, KeyError, json.JSONDecodeError) as exc:
            raise AIProviderError(f"Le fournisseur IA est indisponible : {exc}") from exc


def get_ai_provider() -> BaseAIProvider:
    if settings.AI_PROVIDER == "demo":
        return DemoAIProvider()
    return LLMProvider()
