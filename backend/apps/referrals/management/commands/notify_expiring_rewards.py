from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.services import notify_reward_expiring_soon
from apps.referrals.models import RewardCoupon


class Command(BaseCommand):
    """Notifie les parrains dont une récompense expire dans 7 jours — aucun
    scheduler (Celery/cron) n'existe dans ce projet, cette commande est donc
    destinée à être appelée une fois par jour par un cron du système
    d'exploitation (ex : `0 8 * * * python manage.py notify_expiring_rewards`),
    comme toute future tâche périodique de la plateforme."""

    help = "Notifie les parrains dont une récompense (coupon) disponible expire dans 7 jours."

    def handle(self, *args, **options):
        now = timezone.now()
        window_start = now + timezone.timedelta(days=6, hours=12)
        window_end = now + timezone.timedelta(days=7, hours=12)
        coupons = RewardCoupon.objects.filter(
            status=RewardCoupon.Status.AVAILABLE, expires_at__gte=window_start, expires_at__lte=window_end,
        ).select_related("owner", "tier")
        count = 0
        for coupon in coupons:
            notify_reward_expiring_soon(coupon)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"{count} notification(s) d'expiration envoyée(s)."))
