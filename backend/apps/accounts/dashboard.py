from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.bookings.models import Booking
from apps.events.models import Event
from apps.marketplace.models import MarketplaceListing, MarketplaceSubscription, ProfessionalBookingRequest
from apps.payments.models import Payment
from apps.talents.models import TalentMission, TalentProfile
from apps.tickets.models import Ticket
from apps.training.models import Enrollment

User = get_user_model()


class AdminDashboardView(APIView):
    """Aggregate platform indicators for the administrator dashboard."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        today = timezone.localdate()
        days = min(max(int(request.query_params.get("days", 30)), 7), 90)
        start_date = today - timedelta(days=days - 1)
        start_at = timezone.make_aware(datetime.combine(start_date, time.min))
        now = timezone.now()

        role_labels = dict(User.Role.choices)
        user_roles = {row["role"]: row["total"] for row in User.objects.values("role").annotate(total=Count("id"))}
        users_by_role = [
            {"role": role, "label": label, "total": user_roles.get(role, 0)}
            for role, label in User.Role.choices
        ]

        revenue_rows = Payment.objects.filter(
            status=Payment.Status.COMPLETED,
            currency=Payment.Currency.XAF,
            completed_at__gte=start_at,
        ).annotate(day=TruncDate("completed_at")).values("day").annotate(total=Sum("amount"))
        revenue_by_date = {row["day"].isoformat(): float(row["total"] or 0) for row in revenue_rows}
        user_rows = User.objects.filter(date_joined__gte=start_at).annotate(
            day=TruncDate("date_joined")
        ).values("day").annotate(total=Count("id"))
        users_by_date = {row["day"].isoformat(): row["total"] for row in user_rows}
        revenue_by_day = []
        new_users_by_day = []
        for offset in range(days):
            current_day = (start_date + timedelta(days=offset)).isoformat()
            revenue_by_day.append({"date": current_day, "amount": revenue_by_date.get(current_day, 0)})
            new_users_by_day.append({"date": current_day, "total": users_by_date.get(current_day, 0)})

        completed_xaf = Payment.objects.filter(status=Payment.Status.COMPLETED, currency=Payment.Currency.XAF)
        recent_payments = Payment.objects.select_related("user").order_by("-created_at")[:8]
        recent_users = User.objects.order_by("-date_joined")[:8]
        active_subscriptions = MarketplaceSubscription.objects.filter(expires_at__gt=now)

        return Response({
            "period_days": days,
            "generated_at": now,
            "users": {
                "total": User.objects.count(),
                "active": User.objects.filter(is_active=True).count(),
                "new_period": User.objects.filter(date_joined__gte=start_at).count(),
                "online": User.objects.filter(last_seen__gte=now - timedelta(minutes=5)).count(),
                "by_role": users_by_role,
                "daily": new_users_by_day,
                "recent": [
                    {"id": user.id, "name": user.get_full_name() or user.username, "email": user.email,
                     "role": role_labels.get(user.role, user.role), "joined_at": user.date_joined}
                    for user in recent_users
                ],
            },
            "finance": {
                "revenue_total_xaf": float(completed_xaf.aggregate(total=Sum("amount"))["total"] or 0),
                "revenue_period_xaf": float(completed_xaf.filter(completed_at__gte=start_at).aggregate(total=Sum("amount"))["total"] or 0),
                "revenue_today_xaf": float(completed_xaf.filter(completed_at__date=today).aggregate(total=Sum("amount"))["total"] or 0),
                "completed_payments": completed_xaf.count(),
                "pending_payments": Payment.objects.filter(status=Payment.Status.PENDING).count(),
                "failed_payments": Payment.objects.filter(status=Payment.Status.FAILED).count(),
                "daily": revenue_by_day,
                "recent": [
                    {"id": payment.id, "name": payment.user.get_full_name() or payment.user.username,
                     "amount": float(payment.amount), "currency": payment.currency,
                     "status": payment.get_status_display(), "status_code": payment.status,
                     "purpose": payment.purpose, "created_at": payment.created_at}
                    for payment in recent_payments
                ],
            },
            "activity": {
                "events": Event.objects.count(),
                "published_events": Event.objects.filter(status=Event.Status.PUBLISHED).count(),
                "bookings": Booking.objects.count(),
                "confirmed_bookings": Booking.objects.filter(status=Booking.Status.CONFIRMED).count(),
                "tickets_sold": Ticket.objects.count(),
                "training_enrollments": Enrollment.objects.count(),
                "marketplace_listings": MarketplaceListing.objects.filter(is_active=True).count(),
                "booking_requests": ProfessionalBookingRequest.objects.count(),
                "open_booking_requests": ProfessionalBookingRequest.objects.exclude(status__in=["confirmed", "completed", "declined", "cancelled"]).count(),
                "talents": TalentProfile.objects.count(),
                "active_missions": TalentMission.objects.filter(is_active=True).count(),
                "active_subscriptions": active_subscriptions.count(),
            },
        })
