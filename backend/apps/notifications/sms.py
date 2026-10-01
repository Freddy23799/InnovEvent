"""Architecture SMS interchangeable, sur le même principe que les passerelles de
paiement (apps.payments.gateways). `DemoSmsProvider` journalise sans envoi réel
(fonctionne hors ligne, pour les tests). `TwilioSmsProvider` nécessite les
identifiants réels d'un compte Twilio (ou compatible) avant activation."""

from abc import ABC, abstractmethod

from django.conf import settings


class SmsProviderError(Exception):
    pass


class BaseSmsProvider(ABC):
    @abstractmethod
    def send(self, to: str, message: str) -> None:
        raise NotImplementedError


class DemoSmsProvider(BaseSmsProvider):
    def send(self, to, message):
        return None


class TwilioSmsProvider(BaseSmsProvider):
    def send(self, to, message):
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN or not settings.TWILIO_FROM_NUMBER:
            raise SmsProviderError("SMS non configuré (identifiants Twilio manquants).")
        import requests

        response = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json",
            data={"To": to, "From": settings.TWILIO_FROM_NUMBER, "Body": message},
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            timeout=10,
        )
        if response.status_code >= 300:
            raise SmsProviderError(f"Échec de l'envoi SMS ({response.status_code}) : {response.text}")


def get_sms_provider() -> BaseSmsProvider:
    if settings.SMS_PROVIDER == "twilio":
        return TwilioSmsProvider()
    return DemoSmsProvider()
