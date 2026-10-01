"""Architecture de passerelles de paiement interchangeables (section 10 du CDC).

Chaque passerelle implémente la même interface `charge(payment)` qui renvoie
un tuple (success: bool, provider_reference: str, raw_response: dict).
Aucun secret n'est jamais renvoyé au frontend : ces classes ne s'exécutent
que côté serveur, appelées depuis apps.payments.views.

Seule `DemoGateway` est pleinement fonctionnelle (obligatoire pour les tests,
section 23). Les passerelles réelles nécessitent les identifiants marchands
définitifs (variables d'environnement) et l'intégration de leurs SDK/API
respectifs avant mise en production : la structure est posée, l'appel réseau
réel reste à brancher une fois les comptes marchands PayPal/FreemoPay/KOB
fournis par InnovEvent.
"""

import uuid
from abc import ABC, abstractmethod

from django.conf import settings


class PaymentGatewayError(Exception):
    pass


class BasePaymentGateway(ABC):
    @abstractmethod
    def charge(self, payment):
        """Retourne (success, provider_reference, raw_response)."""
        raise NotImplementedError


class DemoGateway(BasePaymentGateway):
    """Simule une passerelle réelle pour les environnements de test et de recette."""

    def charge(self, payment):
        return True, f"DEMO-{uuid.uuid4().hex[:12].upper()}", {"mode": "demo", "message": "Paiement simulé accepté."}


class PayPalGateway(BasePaymentGateway):
    def charge(self, payment):
        if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_CLIENT_SECRET:
            raise PaymentGatewayError(
                "PayPal n'est pas configuré (PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET manquants)."
            )
        # Intégration réelle à brancher ici via le SDK PayPal Checkout Orders API,
        # une fois les identifiants marchands PayPal fournis.
        raise PaymentGatewayError("Intégration PayPal non finalisée pour cet environnement.")


class MobileMoneyGateway(BasePaymentGateway):
    def charge(self, payment):
        if not settings.FREEMOPAY_API_KEY:
            raise PaymentGatewayError("FreemoPay n'est pas configuré (FREEMOPAY_API_KEY manquant).")
        raise PaymentGatewayError("Intégration Mobile Money / FreemoPay non finalisée pour cet environnement.")


class KobGateway(BasePaymentGateway):
    def charge(self, payment):
        if not settings.KOB_API_KEY:
            raise PaymentGatewayError("KOB n'est pas configuré (KOB_API_KEY manquant).")
        raise PaymentGatewayError("Intégration KOB non finalisée pour cet environnement.")


class CardGateway(BasePaymentGateway):
    """Carte bancaire (Visa / Mastercard) — passerelle à brancher (ex : Stripe,
    FreemoPay carte, ou l'acquéreur retenu par InnovEvent)."""

    def charge(self, payment):
        raise PaymentGatewayError("Intégration carte bancaire non finalisée pour cet environnement.")


GATEWAYS = {
    "demo": DemoGateway,
    "paypal": PayPalGateway,
    "mobile_money": MobileMoneyGateway,
    "mtn_momo": MobileMoneyGateway,
    "orange_money": MobileMoneyGateway,
    "freemopay": MobileMoneyGateway,
    "kob": KobGateway,
    "card": CardGateway,
}


def get_gateway(provider: str) -> BasePaymentGateway:
    if settings.PAYMENTS_DEMO_MODE:
        return DemoGateway()
    gateway_class = GATEWAYS.get(provider)
    if not gateway_class:
        raise PaymentGatewayError(f"Passerelle de paiement inconnue : {provider}")
    return gateway_class()
