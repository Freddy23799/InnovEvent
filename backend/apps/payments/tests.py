import threading
from datetime import timedelta

from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.events.models import Event
from apps.marketplace.models import MarketplaceSubscription, MarketplaceType, SubscriptionPlan
from apps.payments.models import IdempotencyRecord, Payment
from apps.venues.models import Venue

SUBSCRIBE_URL = "/api/v1/marketplace/subscriptions/"


def subscribe_payload():
    return {"marketplace_type": MarketplaceType.VENUES, "plan": "test_plan", "payment_provider": "demo"}


@override_settings(PAYMENTS_DEMO_MODE=True)
class SubscriptionDoublePaymentTests(TestCase):
    def setUp(self):
        SubscriptionPlan.objects.create(
            code="test_plan", label="Test", months=1, duration_days=30, price=1000, marketplace_type=MarketplaceType.VENUES,
        )
        self.user = User.objects.create_user(username="buyer", password="x", role="client")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def payments(self):
        return Payment.objects.filter(user=self.user, purpose="marketplace_subscription").count()

    def test_same_key_is_charged_once_and_replays_response(self):
        first = self.client.post(SUBSCRIBE_URL, subscribe_payload(), format="json", HTTP_IDEMPOTENCY_KEY="key-aaaaaaaa")
        second = self.client.post(SUBSCRIBE_URL, subscribe_payload(), format="json", HTTP_IDEMPOTENCY_KEY="key-aaaaaaaa")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second["Idempotent-Replayed"], "true")
        self.assertEqual(first.data["expires_at"], second.data["expires_at"])
        self.assertEqual(self.payments(), 1)

    def test_new_key_right_after_payment_is_refused(self):
        self.client.post(SUBSCRIBE_URL, subscribe_payload(), format="json", HTTP_IDEMPOTENCY_KEY="key-bbbbbbbb")
        retry = self.client.post(SUBSCRIBE_URL, subscribe_payload(), format="json", HTTP_IDEMPOTENCY_KEY="key-cccccccc")
        self.assertEqual(retry.status_code, 409)
        self.assertEqual(retry.data["code"], "subscription_recently_paid")
        self.assertEqual(self.payments(), 1)

    def test_explicit_renewal_is_allowed(self):
        self.client.post(SUBSCRIBE_URL, subscribe_payload(), format="json", HTTP_IDEMPOTENCY_KEY="key-dddddddd")
        renewal = self.client.post(
            SUBSCRIBE_URL, {**subscribe_payload(), "confirm_renewal": True}, format="json", HTTP_IDEMPOTENCY_KEY="key-eeeeeeee",
        )
        self.assertEqual(renewal.status_code, 200)
        self.assertEqual(self.payments(), 2)

    def test_failed_request_releases_the_key(self):
        bad = self.client.post(
            SUBSCRIBE_URL, {**subscribe_payload(), "plan": "unknown"}, format="json", HTTP_IDEMPOTENCY_KEY="key-ffffffff",
        )
        self.assertEqual(bad.status_code, 400)
        self.assertFalse(IdempotencyRecord.objects.filter(key="key-ffffffff").exists())
        ok = self.client.post(SUBSCRIBE_URL, subscribe_payload(), format="json", HTTP_IDEMPOTENCY_KEY="key-ffffffff")
        self.assertEqual(ok.status_code, 200)

    def test_request_in_progress_returns_conflict(self):
        IdempotencyRecord.objects.create(user=self.user, key="key-gggggggg", scope=f"POST {SUBSCRIBE_URL}")
        response = self.client.post(SUBSCRIBE_URL, subscribe_payload(), format="json", HTTP_IDEMPOTENCY_KEY="key-gggggggg")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.payments(), 0)

    def test_key_is_private_to_its_owner(self):
        other = User.objects.create_user(username="other", password="x", role="client")
        self.client.post(SUBSCRIBE_URL, subscribe_payload(), format="json", HTTP_IDEMPOTENCY_KEY="key-hhhhhhhh")
        other_client = APIClient()
        other_client.force_authenticate(other)
        response = other_client.post(SUBSCRIBE_URL, subscribe_payload(), format="json", HTTP_IDEMPOTENCY_KEY="key-hhhhhhhh")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Idempotent-Replayed", response)
        self.assertEqual(Payment.objects.filter(user=other).count(), 1)


@override_settings(PAYMENTS_DEMO_MODE=True)
class ConcurrentPaymentTests(TransactionTestCase):
    """Deux requêtes réellement simultanées (deux connexions PostgreSQL)."""

    def setUp(self):
        SubscriptionPlan.objects.create(
            code="test_plan", label="Test", months=1, duration_days=30, price=1000, marketplace_type=MarketplaceType.VENUES,
        )
        self.user = User.objects.create_user(username="racer", password="x", role="client")

    def _run_concurrently(self, make_request, count=4):
        results = []
        barrier = threading.Barrier(count)

        def worker(index):
            client = APIClient()
            client.force_authenticate(self.user)
            barrier.wait()
            try:
                results.append(make_request(client, index).status_code)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return results

    def test_simultaneous_clicks_with_same_key_charge_once(self):
        results = self._run_concurrently(
            lambda client, _i: client.post(SUBSCRIBE_URL, subscribe_payload(), format="json", HTTP_IDEMPOTENCY_KEY="key-race0001"),
        )
        self.assertEqual(Payment.objects.filter(user=self.user, status=Payment.Status.COMPLETED).count(), 1)
        self.assertTrue(all(code in (200, 409) for code in results), results)

    def test_simultaneous_tabs_with_different_keys_charge_once(self):
        results = self._run_concurrently(
            lambda client, i: client.post(SUBSCRIBE_URL, subscribe_payload(), format="json", HTTP_IDEMPOTENCY_KEY=f"key-tab0000{i}"),
        )
        self.assertEqual(Payment.objects.filter(user=self.user, status=Payment.Status.COMPLETED).count(), 1)
        self.assertEqual(sorted(results).count(200), 1, results)
        subscription = MarketplaceSubscription.objects.get(user=self.user)
        self.assertLess(subscription.expires_at, timezone.now() + timedelta(days=31))

    def test_simultaneous_booking_payments_charge_once(self):
        user = User.objects.create_user(username="organizer", password="x", role="client")
        event = Event.objects.create(
            title="Gala", organizer=user, start_date=timezone.now() + timedelta(days=30), end_date=timezone.now() + timedelta(days=31),
        )
        venue = Venue.objects.create(name="Salle", city="Douala", capacity=100, price_per_day=50000)
        start = timezone.now() + timedelta(days=30)
        booking = event.bookings.create(
            resource_type="venue", venue=venue, start_datetime=start, end_datetime=start + timedelta(hours=6), created_by=user,
        )
        self.user = user
        self._run_concurrently(
            lambda client, i: client.post(
                f"/api/v1/bookings/{booking.id}/pay/", {"payment_provider": "demo"}, format="json", HTTP_IDEMPOTENCY_KEY=f"key-book000{i}",
            ),
        )
        self.assertEqual(Payment.objects.filter(user=user, purpose="booking", status=Payment.Status.COMPLETED).count(), 1)
