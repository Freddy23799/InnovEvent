from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Payment


@receiver(pre_save, sender=Payment)
def _capture_previous_status(sender, instance, **kwargs):
    """Capture l'ancien statut avant sauvegarde — nécessaire pour détecter une
    transition (et non l'état courant) dans le récepteur `post_save` ci-dessous,
    puisque aucun des appelants existants (bookings/marketplace/tickets/
    training) ne passe par une fonction commune qu'on pourrait modifier une
    seule fois (voir apps/referrals dans le plan)."""
    if instance.pk:
        instance._previous_status = (
            Payment.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
        )
    else:
        instance._previous_status = None


@receiver(post_save, sender=Payment)
def _trigger_referral_processing(sender, instance, created, **kwargs):
    previous_status = getattr(instance, "_previous_status", None)
    if created:
        return
    if previous_status == instance.status:
        return

    from apps.referrals.services import process_payment_completed, process_payment_reversed

    if instance.status == Payment.Status.COMPLETED and previous_status != Payment.Status.COMPLETED:
        process_payment_completed(instance)
    elif previous_status == Payment.Status.COMPLETED and instance.status == Payment.Status.REFUNDED:
        process_payment_reversed(instance)
