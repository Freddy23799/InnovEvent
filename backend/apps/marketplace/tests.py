import io
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.equipment.models import Equipment, StockMovement
from apps.marketplace.models import MarketplaceListing, MarketplaceType, ProfessionalProfile, SaleOrder
from apps.notifications.models import Notification

LISTINGS_URL = "/api/v1/marketplace/listings/"
ORDERS_URL = "/api/v1/marketplace/sale-orders/"
DELIVERY = {
    "delivery_name": "Awa Client", "delivery_phone": "670000000",
    "delivery_city": "Douala", "delivery_address": "Bonapriso, rue 1",
}


class SaleShopTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username="buyer", password="x", role="client")
        self.admin = User.objects.create_user(username="boss", password="x", role="admin")
        self.client = APIClient()
        self.client.force_authenticate(self.buyer)
        # requires_subscription=True : la boutique doit rester visible quand même.
        self.chairs = MarketplaceListing.objects.create(
            marketplace_type=MarketplaceType.SALE, title="Chaise", price=Decimal("2500"), stock=10, requires_subscription=True,
        )
        self.speaker = MarketplaceListing.objects.create(
            marketplace_type=MarketplaceType.SALE, title="Enceinte", price=Decimal("40000"),
        )

    def order(self, items, **extra):
        return self.client.post(ORDERS_URL, {"items": items, **DELIVERY, **extra}, format="json")

    def test_shop_is_visible_without_subscription(self):
        response = self.client.get(LISTINGS_URL, {"marketplace_type": "sale"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual({item["id"] for item in response.json()}, {self.chairs.id, self.speaker.id})

    def test_order_computes_total_server_side_and_decrements_stock(self):
        response = self.order([{"listing": self.chairs.id, "quantity": 4}, {"listing": self.speaker.id, "quantity": 1}])
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(Decimal(data["total"]), Decimal("50000"))
        self.assertEqual(data["status"], "pending_payment")
        self.assertTrue(data["number"].startswith("FAC-"))
        self.chairs.refresh_from_db()
        self.assertEqual(self.chairs.stock, 6)

    def test_order_beyond_stock_is_refused(self):
        response = self.order([{"listing": self.chairs.id, "quantity": 11}])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(SaleOrder.objects.count(), 0)
        self.chairs.refresh_from_db()
        self.assertEqual(self.chairs.stock, 10)

    def test_only_admin_publishes_and_changes_status(self):
        created = self.client.post(LISTINGS_URL, {"marketplace_type": "sale", "title": "X", "price": 1}, format="json")
        self.assertEqual(created.status_code, 400)

        order_id = self.order([{"listing": self.chairs.id, "quantity": 3}]).json()["id"]
        self.assertEqual(self.client.post(f"{ORDERS_URL}{order_id}/set-status/", {"status": "paid"}).status_code, 403)

        self.client.force_authenticate(self.admin)
        cancelled = self.client.post(f"{ORDERS_URL}{order_id}/set-status/", {"status": "cancelled"})
        self.assertEqual(cancelled.status_code, 200)
        self.chairs.refresh_from_db()
        self.assertEqual(self.chairs.stock, 10)

    def test_invoice_pdf_is_generated(self):
        order_id = self.order([{"listing": self.speaker.id, "quantity": 2}], notes="Livrer le matin").json()["id"]
        response = self.client.get(f"{ORDERS_URL}{order_id}/pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content)[:4], b"%PDF")

    def test_buyer_cannot_see_other_orders(self):
        order_id = self.order([{"listing": self.speaker.id, "quantity": 1}]).json()["id"]
        other = User.objects.create_user(username="other", password="x", role="client")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(f"{ORDERS_URL}{order_id}/").status_code, 404)


def png_upload(name="cni.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class VerificationRequestTests(TestCase):
    def setUp(self):
        self.partner = User.objects.create_user(username="presta", password="x", role="partner")
        self.admin = User.objects.create_user(username="boss", password="x", role="admin")
        self.profile = ProfessionalProfile.objects.create(
            user=self.partner, marketplace_type=MarketplaceType.ACTORS, business_name="DJ Test",
        )
        self.client = APIClient()
        self.url = f"/api/v1/marketplace/profiles/{self.profile.id}/"

    def test_profile_saves_without_logo_or_id_card(self):
        self.client.force_authenticate(self.partner)
        response = self.client.patch(self.url, {"description": "Sans photo ni CNI"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.verification_requested_at)

    def test_id_card_upload_requests_verification_and_admin_decision_clears_it(self):
        self.client.force_authenticate(self.partner)
        response = self.client.patch(self.url, {"id_card_photo": png_upload()}, format="multipart")
        self.assertEqual(response.status_code, 200, response.content)
        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.verification_requested_at)
        self.assertTrue(Notification.objects.filter(recipient=self.admin, title="Demande de vérification").exists())

        self.client.force_authenticate(self.admin)
        response = self.client.patch(f"{self.url}badges/", {"verification_status": "identity_verified"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.verification_requested_at)
        self.assertEqual(self.profile.verification_status, "identity_verified")
        self.assertTrue(Notification.objects.filter(recipient=self.partner, title="Vérification de votre profil").exists())


class SaleRentalTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username="loueur", password="x", role="client")
        self.admin = User.objects.create_user(username="boss", password="x", role="admin")
        self.client = APIClient()
        self.client.force_authenticate(self.client_user)
        # 200 chaises en inventaire, proposées à la vente et à la location.
        self.equipment = Equipment.objects.create(name="Chaise Chiavari", quantity_total=200)
        self.chairs = MarketplaceListing.objects.create(
            marketplace_type=MarketplaceType.SALE, title="Chaise Chiavari", price=Decimal("15000"),
            is_for_sale=True, is_for_rent=True, rental_price_per_day=Decimal("500"), equipment=self.equipment,
        )
        self.start = timezone.localdate() + timedelta(days=10)

    def rent(self, quantity, start, days):
        return self.client.post(ORDERS_URL, {
            "items": [{"listing": self.chairs.id, "quantity": quantity}], "order_type": "rental",
            "rental_start": start.isoformat(), "rental_end": (start + timedelta(days=days - 1)).isoformat(), **DELIVERY,
        }, format="json")

    def test_rental_total_uses_days_and_does_not_move_stock(self):
        response = self.rent(200, self.start, 2)
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(Decimal(data["total"]), Decimal("200000"))  # 200 × 500 × 2 jours
        self.assertEqual(data["rental_days"], 2)
        self.assertEqual(data["rental_status"], "reserved")
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.quantity_total, 200)

    def test_overlapping_rental_is_refused_but_other_dates_are_free(self):
        self.assertEqual(self.rent(150, self.start, 2).status_code, 201)
        self.assertEqual(self.rent(60, self.start + timedelta(days=1), 3).status_code, 409)
        self.assertEqual(self.rent(60, self.start + timedelta(days=2), 3).status_code, 201)
        check = self.client.post(f"{ORDERS_URL}check-availability/", {
            "items": [{"listing": self.chairs.id, "quantity": 100}], "order_type": "rental",
            "rental_start": self.start.isoformat(), "rental_end": self.start.isoformat(),
        }, format="json").json()
        self.assertEqual(check["lines"][0]["available"], 50)
        self.assertFalse(check["ok"])

    def test_purchase_creates_stock_movement(self):
        response = self.client.post(ORDERS_URL, {"items": [{"listing": self.chairs.id, "quantity": 10}], **DELIVERY}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.quantity_total, 190)
        self.assertTrue(StockMovement.objects.filter(equipment=self.equipment, reason="sale", quantity=10).exists())

    def test_return_with_damage_removes_pieces_from_inventory(self):
        order = self.rent(100, self.start, 1).json()
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(f"{ORDERS_URL}{order['id']}/mark-out/").status_code, 200)
        item_id = order["items"][0]["id"]
        response = self.client.post(f"{ORDERS_URL}{order['id']}/mark-returned/", {
            "items": [{"item": item_id, "damaged_quantity": 3, "lost_quantity": 1}], "notes": "3 cassées",
        }, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["rental_status"], "returned")
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.quantity_total, 196)

    def test_rental_refused_for_sale_only_product(self):
        self.chairs.is_for_rent = False
        self.chairs.save()
        self.assertEqual(self.rent(1, self.start, 1).status_code, 400)


class RentalPriceTests(TestCase):
    def test_rental_price_defaults_to_ten_percent_rounded(self):
        listing = MarketplaceListing(marketplace_type=MarketplaceType.SALE, title="Verre", price=Decimal("2500"))
        self.assertEqual(listing.rental_price, Decimal("250"))
        listing.price = Decimal("12500")
        self.assertEqual(listing.rental_price, Decimal("1250"))
        listing.price = Decimal("300")
        self.assertEqual(listing.rental_price, Decimal("50"))
        listing.rental_price_per_day = Decimal("400")
        self.assertEqual(listing.rental_price, Decimal("400"))
        listing.is_for_rent = False
        self.assertIsNone(listing.rental_price)


class ReminderTests(TestCase):
    def setUp(self):
        from apps.accounts.models import User

        self.admin = User.objects.create_user(username="boss", password="x", role="admin")
        self.client_user = User.objects.create_user(username="relance", password="x", role="client", first_name="Awa")
        self.listing = MarketplaceListing.objects.create(marketplace_type=MarketplaceType.SALE, title="Verre", price=Decimal("2500"))
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)

    def test_abandoned_cart_is_reminded_once_by_the_assistant(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.marketplace.models import CartSnapshot
        from apps.marketplace.reminders import run_all_reminders
        from apps.messaging.models import Message

        response = self.api.put("/api/v1/marketplace/cart/", {"items": [{"listing": self.listing.id, "quantity": 4}], "mode": "rental"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["total"], "1000.00")  # 4 × 250 / jour
        later = timezone.now() + timedelta(hours=3)
        self.assertEqual(run_all_reminders(later)["paniers"], 1)
        self.assertEqual(run_all_reminders(later)["paniers"], 0)
        self.assertTrue(Notification.objects.filter(recipient=self.client_user, title__startswith="Votre panier").exists())
        self.assertTrue(Message.objects.filter(conversation__participants=self.client_user, is_automated=True).exists())
        # Commander supprime le panier serveur.
        self.api.post(ORDERS_URL, {"items": [{"listing": self.listing.id, "quantity": 1}], **DELIVERY}, format="json")
        self.assertFalse(CartSnapshot.objects.filter(user=self.client_user).exists())

    def test_unpaid_invoice_is_reminded_after_a_day_and_order_notifies(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.marketplace.reminders import run_all_reminders

        self.api.post(ORDERS_URL, {"items": [{"listing": self.listing.id, "quantity": 2}], **DELIVERY}, format="json")
        self.assertTrue(Notification.objects.filter(recipient=self.admin, title__startswith="Nouvelle commande").exists())
        self.assertEqual(run_all_reminders(timezone.now())["factures"], 0)
        self.assertEqual(run_all_reminders(timezone.now() + timedelta(hours=25))["factures"], 1)
