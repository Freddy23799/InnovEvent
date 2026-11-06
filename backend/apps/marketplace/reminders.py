"""Relances automatiques de l'assistant InnovEvent.

Chaque relance poste un court message dans la conversation de support du
client et lui envoie une notification (temps réel + push) qui ouvre
directement la bonne page. Une seule relance par situation : la date de
relance est mémorisée pour ne jamais harceler le client.
"""

from datetime import timedelta

from django.db.models import F, Q
from django.utils import timezone

from apps.messaging.services import assistant_follow_up

from .models import CartSnapshot, MarketplaceSubscription, Quote, SaleOrder

CART_IDLE = timedelta(hours=2)
INVOICE_UNPAID = timedelta(hours=24)
QUOTE_PENDING = timedelta(hours=24)
SUBSCRIPTION_NOTICE = timedelta(days=3)


def _money(amount, currency="XAF"):
    return f"{amount:,.0f} {'FCFA' if currency == 'XAF' else currency}".replace(",", " ")


def _name(user):
    return user.first_name or user.username


def remind_abandoned_carts(now):
    count = 0
    carts = CartSnapshot.objects.select_related("user").filter(
        updated_at__lte=now - CART_IDLE, item_count__gt=0,
    ).filter(Q(reminded_at__isnull=True) | Q(reminded_at__lt=F("updated_at")))
    for cart in carts:
        what = "votre location" if cart.mode == "rental" else "votre commande"
        assistant_follow_up(
            cart.user,
            body=(
                f"Bonjour {_name(cart.user)} 👋 Votre panier vous attend : {cart.item_count} pièce(s), "
                f"{_money(cart.total, cart.currency)}. Finalisez {what} en un clic : Boutique › Panier › Passer la commande."
            ),
            title="Votre panier vous attend 🛒",
            link="/app/boutique/commande",
        )
        CartSnapshot.objects.filter(pk=cart.pk).update(reminded_at=now)
        count += 1
    return count


def remind_unpaid_invoices(now):
    count = 0
    orders = SaleOrder.objects.select_related("buyer").filter(
        status=SaleOrder.Status.PENDING_PAYMENT, payment_reminded_at__isnull=True, created_at__lte=now - INVOICE_UNPAID,
    )
    for order in orders:
        assistant_follow_up(
            order.buyer,
            body=(
                f"Bonjour {_name(order.buyer)} 👋 Votre facture {order.number} ({_money(order.total, order.currency)}) "
                "est en attente de paiement. Besoin d'aide pour la régler ou organiser la livraison ? Répondez-moi ici."
            ),
            title=f"Facture {order.number} en attente de paiement",
            link=f"/app/boutique/commandes/{order.id}",
        )
        SaleOrder.objects.filter(pk=order.pk).update(payment_reminded_at=now)
        count += 1
    return count


def remind_pending_quotes(now):
    count = 0
    quotes = Quote.objects.select_related("booking_request__client", "booking_request__profile").filter(
        reminded_at__isnull=True, updated_at__lte=now - QUOTE_PENDING,
    ).filter(Q(status=Quote.Status.SENT) | Q(status=Quote.Status.ACCEPTED, payment__isnull=True))
    for quote in quotes:
        client = quote.booking_request.client
        provider = quote.booking_request.profile.business_name
        if quote.status == Quote.Status.SENT:
            body = f"Bonjour {_name(client)} 👋 {provider} vous a envoyé un devis. Consultez-le et répondez dans « Mes demandes prestataires »."
            title = f"Devis de {provider} en attente de votre réponse"
        else:
            body = f"Bonjour {_name(client)} 👋 Vous avez accepté le devis de {provider}. Réglez-le pour confirmer la prestation dans « Mes demandes prestataires »."
            title = f"Confirmez votre devis avec {provider}"
        assistant_follow_up(client, body=body, title=title, link="/app/my-booking-requests")
        Quote.objects.filter(pk=quote.pk).update(reminded_at=now)
        count += 1
    return count


def remind_expiring_subscriptions(now):
    count = 0
    subscriptions = MarketplaceSubscription.objects.select_related("user").filter(
        expires_at__gt=now, expires_at__lte=now + SUBSCRIPTION_NOTICE, expiry_reminded_at__isnull=True,
    )
    for sub in subscriptions:
        assistant_follow_up(
            sub.user,
            body=(
                f"Bonjour {_name(sub.user)} 👋 Votre abonnement « {sub.get_marketplace_type_display()} » expire le "
                f"{timezone.localtime(sub.expires_at):%d/%m/%Y}. Renouvelez-le depuis Marketplace pour garder l'accès."
            ),
            title="Votre abonnement expire bientôt",
            link="/app/premium-marketplace",
        )
        MarketplaceSubscription.objects.filter(pk=sub.pk).update(expiry_reminded_at=now)
        count += 1
    return count


def run_all_reminders(now=None):
    now = now or timezone.now()
    return {
        "paniers": remind_abandoned_carts(now),
        "factures": remind_unpaid_invoices(now),
        "devis": remind_pending_quotes(now),
        "abonnements": remind_expiring_subscriptions(now),
    }
