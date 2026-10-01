from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.deliveries.models import Carrier, Delivery, DeliveryExpense, DeliveryStatusHistory, DeliveryZone, Driver, Parcel, Vehicle

User = get_user_model()


class Command(BaseCommand):
    help = "Crée des données de démonstration réalistes pour le module Transport & Livraison."

    def handle(self, *args, **options):
        zones = self.seed_zones()
        carriers = self.seed_carriers(zones)
        vehicles = self.seed_vehicles(carriers)
        drivers = self.seed_drivers(carriers, vehicles)
        self.seed_carrier_account(carriers[2])
        self.seed_deliveries(zones, carriers, drivers, vehicles)
        self.seed_expenses(carriers, vehicles)
        self.stdout.write(self.style.SUCCESS("Données de démonstration Transport & Livraison créées."))

    def seed_carrier_account(self, carrier):
        """Compte de démonstration pour l'espace « Transporteur » — lié à
        Kamga Transport, qui a déjà des livraisons/chauffeurs/véhicules
        fictifs assignés (voir `seed_deliveries`/`seed_vehicles`/`seed_drivers`)."""
        user, created = User.objects.get_or_create(
            username="transporteur_demo",
            defaults=dict(
                email="transporteur.demo@innovevent.test", first_name="Paul", last_name="Kamga",
                role=User.Role.PARTNER, is_verified=True,
            ),
        )
        if created:
            user.set_password("Transporteur!2026")
            user.save()
        if carrier.user_id != user.id:
            carrier.user = user
            carrier.save(update_fields=["user"])
        self.stdout.write(f"Compte transporteur de démonstration : transporteur_demo / Transporteur!2026 (lié à « {carrier.name} »).")

    def seed_zones(self):
        specs = [
            {"name": "Zone A - Douala centre", "base_fee": 1000, "price_per_km": 150, "price_per_kg": 50, "urgent_surcharge_percent": 20, "order": 1},
            {"name": "Zone B - Douala périphérie", "base_fee": 1500, "price_per_km": 200, "price_per_kg": 75, "urgent_surcharge_percent": 25, "order": 2},
            {"name": "Zone C - Interurbain", "base_fee": 3000, "price_per_km": 250, "price_per_kg": 100, "urgent_surcharge_percent": 30, "order": 3},
        ]
        zones = []
        for spec in specs:
            zone, _ = DeliveryZone.objects.get_or_create(name=spec["name"], defaults=spec)
            zones.append(zone)
        self.stdout.write(f"{len(zones)} zone(s) tarifaire(s).")
        return zones

    def seed_carriers(self, zones):
        specs = [
            {"name": "InnovEvent Logistique", "carrier_type": Carrier.CarrierType.INTERNAL, "phone": "+237690000001", "service_zone": zones[0]},
            {"name": "Rapid Moto Express", "carrier_type": Carrier.CarrierType.PARTNER, "phone": "+237690000002", "service_zone": zones[1]},
            {"name": "Kamga Transport", "carrier_type": Carrier.CarrierType.INDEPENDENT, "phone": "+237690000003", "service_zone": zones[2]},
        ]
        carriers = []
        for spec in specs:
            carrier, _ = Carrier.objects.get_or_create(name=spec["name"], defaults=spec)
            carriers.append(carrier)
        self.stdout.write(f"{len(carriers)} transporteur(s).")
        return carriers

    def seed_vehicles(self, carriers):
        specs = [
            {"plate_number": "LT-001-CM", "vehicle_type": Vehicle.VehicleType.MOTO, "capacity_kg": 30, "carrier": carriers[0]},
            {"plate_number": "LT-002-CM", "vehicle_type": Vehicle.VehicleType.VAN, "capacity_kg": 800, "carrier": carriers[0]},
            {"plate_number": "LT-003-CM", "vehicle_type": Vehicle.VehicleType.PICKUP, "capacity_kg": 1200, "carrier": carriers[1]},
            {"plate_number": "LT-004-CM", "vehicle_type": Vehicle.VehicleType.TRUCK, "capacity_kg": 3000, "carrier": carriers[2]},
            {"plate_number": "LT-005-CM", "vehicle_type": Vehicle.VehicleType.VAN, "capacity_kg": 900, "carrier": carriers[2]},
        ]
        vehicles = []
        for spec in specs:
            vehicle, _ = Vehicle.objects.get_or_create(plate_number=spec["plate_number"], defaults=spec)
            vehicles.append(vehicle)
        self.stdout.write(f"{len(vehicles)} véhicule(s).")
        return vehicles

    def seed_drivers(self, carriers, vehicles):
        linked_user = User.objects.filter(username="employe_demo").first()
        specs = [
            {"full_name": "Jean Mbarga", "phone": "+237691000001", "carrier": carriers[0], "current_vehicle": vehicles[0], "user": linked_user},
            {"full_name": "Paul Nkomo", "phone": "+237691000002", "carrier": carriers[0], "current_vehicle": vehicles[1]},
            {"full_name": "Samuel Eto", "phone": "+237691000003", "carrier": carriers[1], "current_vehicle": vehicles[2]},
            {"full_name": "Andre Fouda", "phone": "+237691000004", "carrier": carriers[2], "current_vehicle": vehicles[3]},
            {"full_name": "Cedric Tchoumi", "phone": "+237691000005", "carrier": carriers[2], "current_vehicle": vehicles[4]},
        ]
        drivers = []
        for spec in specs:
            driver, _ = Driver.objects.get_or_create(full_name=spec["full_name"], defaults=spec)
            drivers.append(driver)
        self.stdout.write(f"{len(drivers)} chauffeur(s), dont 1 lié à un compte utilisateur ({'oui' if linked_user else 'non — employe_demo introuvable'}).")
        return drivers

    def seed_deliveries(self, zones, carriers, drivers, vehicles):
        client = User.objects.filter(username="client_demo").first()
        today = timezone.now().date()

        specs = [
            {"status": Delivery.Status.PENDING, "destination_address": "Akwa, Douala", "zone": zones[0]},
            {"status": Delivery.Status.CONFIRMED, "destination_address": "Bonapriso, Douala", "zone": zones[0]},
            {"status": Delivery.Status.TO_PREPARE, "destination_address": "Bonamoussadi, Douala", "zone": zones[1]},
            {
                "status": Delivery.Status.CARRIER_ASSIGNED, "destination_address": "Logbaba, Douala", "zone": zones[1],
                "carrier": carriers[0], "driver": drivers[0], "vehicle": vehicles[0],
            },
            {
                "status": Delivery.Status.IN_TRANSIT, "destination_address": "Yaoundé centre-ville", "zone": zones[2],
                "carrier": carriers[2], "driver": drivers[3], "vehicle": vehicles[3],
            },
            {
                "status": Delivery.Status.DELIVERED, "destination_address": "Deido, Douala", "zone": zones[0],
                "carrier": carriers[0], "driver": drivers[1], "vehicle": vehicles[1],
            },
            {"status": Delivery.Status.CANCELLED, "destination_address": "Ndokoti, Douala", "zone": zones[1]},
            {
                "status": Delivery.Status.FAILED, "destination_address": "New-Bell, Douala", "zone": zones[0],
                "carrier": carriers[1], "driver": drivers[2],
            },
            # Livraisons supplémentaires pour Kamga Transport (carriers[2]) —
            # portefeuille varié pour l'espace « Transporteur » de démonstration.
            {
                "status": Delivery.Status.DELIVERED, "destination_address": "Bastos, Yaoundé", "zone": zones[2],
                "carrier": carriers[2], "driver": drivers[4], "vehicle": vehicles[4],
            },
            {
                "status": Delivery.Status.DELIVERING, "destination_address": "Mvog-Mbi, Yaoundé", "zone": zones[2],
                "carrier": carriers[2], "driver": drivers[3], "vehicle": vehicles[3],
            },
            {
                "status": Delivery.Status.CARRIER_ASSIGNED, "destination_address": "Essos, Yaoundé", "zone": zones[2],
                "carrier": carriers[2], "driver": drivers[4], "vehicle": vehicles[4],
            },
            {
                "status": Delivery.Status.FAILED, "destination_address": "Nkoldongo, Yaoundé", "zone": zones[2],
                "carrier": carriers[2], "driver": drivers[3],
            },
        ]

        created_count = 0
        for i, spec in enumerate(specs):
            reference_seed = f"Livraison démo #{i + 1}"
            if Delivery.objects.filter(description=reference_seed).exists():
                continue
            zone = spec.pop("zone")
            status = spec.pop("status")
            delivery = Delivery.objects.create(
                client=client,
                client_phone="+237699000000",
                sender_name="InnovEvent Group",
                sender_phone="+237690000000",
                pickup_address="Siège InnovEvent, Bonanjo, Douala",
                recipient_name=f"Client {i + 1}",
                recipient_phone="+237698000000",
                description=reference_seed,
                zone=zone,
                distance_km=8 + i,
                amount=zone.base_fee + zone.price_per_km * (8 + i),
                scheduled_date=today + timedelta(days=i % 4),
                status=status,
                **spec,
            )
            Parcel.objects.create(delivery=delivery, description="Colis événementiel", quantity=1, weight_kg=5 + i)
            DeliveryStatusHistory.objects.create(delivery=delivery, old_status="", new_status=Delivery.Status.CREATED, comment="Création (démo)")
            if status != Delivery.Status.CREATED:
                DeliveryStatusHistory.objects.create(delivery=delivery, old_status=Delivery.Status.CREATED, new_status=status, comment="Progression (démo)")
            created_count += 1

        self.stdout.write(f"{created_count} livraison(s) de démonstration créée(s).")

    def seed_expenses(self, carriers, vehicles):
        specs = [
            {"category": DeliveryExpense.Category.FUEL, "amount": 15000, "description": "Plein LT-004-CM", "carrier": carriers[2], "vehicle": vehicles[3]},
            {"category": DeliveryExpense.Category.TOLL, "amount": 2500, "description": "Péage Douala-Yaoundé", "carrier": carriers[2], "vehicle": vehicles[3]},
            {"category": DeliveryExpense.Category.MAINTENANCE, "amount": 45000, "description": "Vidange LT-005-CM", "carrier": carriers[2], "vehicle": vehicles[4]},
        ]
        created_count = 0
        for spec in specs:
            _, created = DeliveryExpense.objects.get_or_create(description=spec["description"], defaults=spec)
            created_count += 1 if created else 0
        self.stdout.write(f"{created_count} dépense(s) transport de démonstration créée(s).")
