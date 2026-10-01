import secrets
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.documents.validators import validate_image_file


class DeliveryZone(models.Model):
    """Zone tarifaire (« Zone A », « Zone B »...) — tarification simple et
    transparente, entièrement configurable par l'administration, sans
    déploiement (section 12/13 du cahier des charges transport)."""

    name = models.CharField(max_length=100, unique=True)
    base_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    urgent_surcharge_percent = models.PositiveSmallIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Zone tarifaire"
        verbose_name_plural = "Zones tarifaires"

    def __str__(self):
        return self.name


class Carrier(models.Model):
    """Transporteur : entreprise, partenaire, indépendant ou interne."""

    class CarrierType(models.TextChoices):
        COMPANY = "company", "Entreprise"
        PARTNER = "partner", "Partenaire"
        INDEPENDENT = "independent", "Indépendant"
        INTERNAL = "internal", "Interne"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Disponible"
        BUSY = "busy", "Occupé"
        OFF_DUTY = "off_duty", "Hors service"
        SUSPENDED = "suspended", "Suspendu"
        INACTIVE = "inactive", "Inactif"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="carrier_profile",
        help_text="Compte utilisateur lié (facultatif) — donne accès à l'espace « Transporteur » (gestion de sa propre flotte et de ses livraisons).",
    )
    name = models.CharField(max_length=150)
    company_name = models.CharField(max_length=150, blank=True)
    carrier_type = models.CharField(max_length=20, choices=CarrierType.choices, default=CarrierType.INDEPENDENT)
    phone = models.CharField(max_length=30)
    whatsapp = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    service_zone = models.ForeignKey(DeliveryZone, on_delete=models.SET_NULL, null=True, blank=True, related_name="carriers")
    transport_type = models.CharField(max_length=100, blank=True, help_text="Ex : moto, camion, mixte...")
    id_number = models.CharField(max_length=50, blank=True, help_text="Numéro d'identification / RCCM")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    documents = models.FileField(upload_to="deliveries/carriers/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Transporteur"
        verbose_name_plural = "Transporteurs"

    def __str__(self):
        return self.name

    @property
    def deliveries_count(self):
        return self.deliveries.count()


class Vehicle(models.Model):
    class VehicleType(models.TextChoices):
        MOTO = "moto", "Moto"
        TRICYCLE = "tricycle", "Tricycle"
        CAR = "car", "Voiture"
        PICKUP = "pickup", "Pickup"
        VAN = "van", "Camionnette"
        TRUCK = "truck", "Camion"
        OTHER = "other", "Autre"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Disponible"
        IN_USE = "in_use", "En mission"
        MAINTENANCE = "maintenance", "En maintenance"
        UNAVAILABLE = "unavailable", "Indisponible"

    plate_number = models.CharField(max_length=30, unique=True)
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices, default=VehicleType.CAR)
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_volume_m3 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mileage_km = models.PositiveIntegerField(default=0)
    consumption_l_100km = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    carrier = models.ForeignKey(Carrier, on_delete=models.SET_NULL, null=True, blank=True, related_name="vehicles")
    insurance_expiry = models.DateField(null=True, blank=True)
    technical_inspection_expiry = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    photo = models.ImageField(upload_to="deliveries/vehicles/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["plate_number"]
        verbose_name = "Véhicule"
        verbose_name_plural = "Véhicules"

    def __str__(self):
        return f"{self.plate_number} ({self.get_vehicle_type_display()})"

    @property
    def is_insurance_expiring_soon(self):
        if not self.insurance_expiry:
            return False
        return 0 <= (self.insurance_expiry - timezone.now().date()).days <= 30

    @property
    def is_inspection_expiring_soon(self):
        if not self.technical_inspection_expiry:
            return False
        return 0 <= (self.technical_inspection_expiry - timezone.now().date()).days <= 30


class Driver(models.Model):
    """Chauffeur — interne (lié à un transporteur « interne ») ou externe.
    Le lien `user` est facultatif : s'il est renseigné, ce compte existant
    (rôle employé ou prestataire, peu importe) accède en plus à « Mes
    livraisons », sans qu'un nouveau rôle applicatif soit nécessaire."""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Disponible"
        ON_MISSION = "on_mission", "En mission"
        OFF_DUTY = "off_duty", "Hors service"
        SUSPENDED = "suspended", "Suspendu"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="driver_profile",
        help_text="Compte utilisateur lié (facultatif) — donne accès à l'espace « Mes livraisons ».",
    )
    full_name = models.CharField(max_length=150)
    photo = models.ImageField(
        upload_to="deliveries/drivers/", blank=True, null=True, validators=[validate_image_file], help_text="Photo du chauffeur.",
    )
    id_card_photo = models.ImageField(
        upload_to="deliveries/drivers/id_cards/", blank=True, null=True, validators=[validate_image_file],
        help_text="Photo de la CNI.",
    )
    license_photo = models.ImageField(
        upload_to="deliveries/drivers/licenses/", blank=True, null=True, validators=[validate_image_file],
        help_text="Photo du permis de conduire.",
    )
    phone = models.CharField(max_length=30)
    whatsapp = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    license_number = models.CharField(max_length=50, blank=True)
    license_category = models.CharField(max_length=20, blank=True)
    license_expiry = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    carrier = models.ForeignKey(Carrier, on_delete=models.SET_NULL, null=True, blank=True, related_name="drivers")
    current_vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name="drivers")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    documents = models.FileField(upload_to="deliveries/drivers/documents/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name = "Chauffeur"
        verbose_name_plural = "Chauffeurs"

    def __str__(self):
        return self.full_name

    @property
    def is_license_expiring_soon(self):
        if not self.license_expiry:
            return False
        return 0 <= (self.license_expiry - timezone.now().date()).days <= 30

    @property
    def deliveries_count(self):
        return self.deliveries.count()


def _generate_delivery_reference():
    """Référence lisible et séquentielle par année, façon `Enrollment.matricule`
    (apps.training) : LIV-2026-000001, LIV-2026-000002..."""
    year = timezone.now().year
    last = Delivery.objects.filter(reference__startswith=f"LIV-{year}-").order_by("-id").first()
    sequence = int(last.reference.split("-")[-1]) + 1 if last else 1
    return f"LIV-{year}-{sequence:06d}"


def _generate_tracking_code():
    """Code court et tapable par un client sur la page de suivi publique —
    distinct du QR de vérification des documents PDF (voir apps.deliveries.pdf),
    qui réutilise le mécanisme de signature existant (apps.documents.signing)."""
    code = f"TRK-{secrets.token_hex(4).upper()}"
    while Delivery.objects.filter(tracking_code=code).exists():
        code = f"TRK-{secrets.token_hex(4).upper()}"
    return code


class Delivery(models.Model):
    """Livraison — cœur du module. Statuts, tarification, affectation,
    intégration paiement (réutilise apps.payments.Payment)."""

    class DeliveryType(models.TextChoices):
        LOCAL = "local", "Livraison locale"
        INTERCITY = "intercity", "Livraison interurbaine"
        GOODS = "goods", "Marchandises"
        PARCEL = "parcel", "Colis"
        LINKED_ORDER = "linked_order", "Liée à une commande"
        INDEPENDENT = "independent", "Indépendante"

    class Priority(models.TextChoices):
        NORMAL = "normal", "Normale"
        URGENT = "urgent", "Urgente"

    class PaymentMode(models.TextChoices):
        BEFORE = "before", "Avant livraison"
        ON_DELIVERY = "on_delivery", "À la livraison"

    class Status(models.TextChoices):
        CREATED = "created", "Créée"
        PENDING = "pending", "En attente"
        CONFIRMED = "confirmed", "Confirmée"
        TO_PREPARE = "to_prepare", "À préparer"
        READY = "ready", "Prête à récupérer"
        CARRIER_ASSIGNED = "carrier_assigned", "Transporteur affecté"
        COLLECTED = "collected", "Collectée"
        IN_TRANSIT = "in_transit", "En transit"
        ARRIVED = "arrived", "Arrivée à destination"
        DELIVERING = "delivering", "En cours de livraison"
        DELIVERED = "delivered", "Livrée"
        FAILED = "failed", "Échec de livraison"
        POSTPONED = "postponed", "Reportée"
        CANCELLED = "cancelled", "Annulée"
        RETURNING = "returning", "Retour en cours"
        RETURNED = "returned", "Retournée"

    ACTIVE_STATUSES = [
        Status.PENDING, Status.CONFIRMED, Status.TO_PREPARE, Status.READY, Status.CARRIER_ASSIGNED,
        Status.COLLECTED, Status.IN_TRANSIT, Status.ARRIVED, Status.DELIVERING,
    ]
    # Transitions permises pour un chauffeur depuis son espace « Mes livraisons »
    # (section 15) — volontairement restreint par rapport aux statuts complets
    # que l'administration peut poser librement.
    DRIVER_ALLOWED_TRANSITIONS = {
        Status.CARRIER_ASSIGNED: Status.COLLECTED,
        Status.COLLECTED: Status.IN_TRANSIT,
        Status.IN_TRANSIT: Status.DELIVERING,
        Status.DELIVERING: Status.DELIVERED,
    }

    reference = models.CharField(max_length=30, unique=True, editable=False)
    tracking_code = models.CharField(max_length=20, unique=True, editable=False)

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")
    client_phone = models.CharField(max_length=30, blank=True)

    sender_name = models.CharField(max_length=150, blank=True)
    sender_phone = models.CharField(max_length=30, blank=True)
    pickup_address = models.CharField(max_length=255)

    recipient_name = models.CharField(max_length=150, blank=True)
    recipient_phone = models.CharField(max_length=30, blank=True)
    destination_address = models.CharField(max_length=255)

    delivery_type = models.CharField(max_length=20, choices=DeliveryType.choices, default=DeliveryType.PARCEL)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    description = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)

    zone = models.ForeignKey(DeliveryZone, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    payment_mode = models.CharField(max_length=20, choices=PaymentMode.choices, default=PaymentMode.ON_DELIVERY)
    payment = models.ForeignKey("payments.Payment", on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")

    carrier = models.ForeignKey(Carrier, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_time = models.TimeField(null=True, blank=True)
    internal_notes = models.TextField(blank=True)

    # Dernière position connue du chauffeur (Phase 2 — suivi cartographique
    # léger, sans fournisseur de cartes payant : OpenStreetMap/Leaflet côté
    # frontend). Mise à jour par le chauffeur lui-même pendant le transport,
    # jamais exposée sur le suivi public (section 6 — confidentialité).
    last_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_at = models.DateTimeField(null=True, blank=True)

    # Position partagée par le CLIENT (destinataire) le temps du transport,
    # pour faciliter la livraison — jamais permanente : effacée automatiquement
    # dès que la livraison est confirmée (voir DeliveryViewSet.change_status /
    # confirm_proof), donc jamais conservée au-delà du besoin.
    client_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    client_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    client_location_at = models.DateTimeField(null=True, blank=True)

    # Anticipe l'intégration future avec une commande existante (Phase 2 —
    # section 18 du cahier des charges) sans nécessiter de migration
    # destructive plus tard. Non exploité par l'interface en Phase 1.
    related_booking = models.ForeignKey("bookings.Booking", on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")
    related_marketplace_order = models.ForeignKey("marketplace.MarketplaceOrder", on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Livraison"
        verbose_name_plural = "Livraisons"

    def __str__(self):
        return f"{self.reference} — {self.destination_address}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = _generate_delivery_reference()
        if not self.tracking_code:
            self.tracking_code = _generate_tracking_code()
        super().save(*args, **kwargs)

    @property
    def is_ongoing(self):
        return self.status in self.ACTIVE_STATUSES

    def estimate_amount(self):
        """Formule transparente : tarif de base + distance + poids + urgence
        (section 13), puis application en cascade des règles de tarification
        avancées (`PricingRule`, Phase 2) correspondant au véhicule/priorité/
        poids de la livraison. Ne modifie jamais `amount` elle-même — c'est à
        l'appelant de décider de l'appliquer (l'administration garde la main
        pour ajuster)."""
        total_weight = sum((p.weight_kg or 0) for p in self.parcels.all())
        if not self.zone:
            total = self.amount
        else:
            total = self.zone.base_fee
            if self.distance_km:
                total += self.zone.price_per_km * self.distance_km
            if total_weight:
                total += self.zone.price_per_kg * Decimal(str(total_weight))
            if self.priority == self.Priority.URGENT and self.zone.urgent_surcharge_percent:
                total += total * Decimal(self.zone.urgent_surcharge_percent) / Decimal(100)

        vehicle_type = self.vehicle.vehicle_type if self.vehicle else ""
        weight_kg = Decimal(str(total_weight)) if total_weight else None
        for rule in PricingRule.objects.filter(is_active=True).select_related("zone"):
            if rule.matches(zone=self.zone, vehicle_type=vehicle_type, priority=self.priority, weight_kg=weight_kg):
                total += rule.extra_fee
                if rule.multiplier_percent:
                    total += total * Decimal(rule.multiplier_percent) / Decimal(100)

        return total.quantize(Decimal("1"))


class Parcel(models.Model):
    """Colis constitutif d'une livraison — une livraison peut en contenir
    plusieurs (section 11)."""

    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name="parcels")
    description = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dimensions = models.CharField(max_length=100, blank=True, help_text="Ex : 40x30x20 cm")
    declared_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_fragile = models.BooleanField(default=False)
    is_insured = models.BooleanField(default=False)
    special_instructions = models.TextField(blank=True)
    photo = models.ImageField(upload_to="deliveries/parcels/", blank=True, null=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Colis"
        verbose_name_plural = "Colis"

    def __str__(self):
        return f"{self.description} × {self.quantity}"


class DeliveryStatusHistory(models.Model):
    """Historique des changements de statut — aucun pattern équivalent
    n'existait ailleurs dans le projet ; nécessaire pour la timeline de suivi
    (sections 5, 6, 32)."""

    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name="status_history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    old_status = models.CharField(max_length=20, choices=Delivery.Status.choices, blank=True)
    new_status = models.CharField(max_length=20, choices=Delivery.Status.choices)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Historique de statut"
        verbose_name_plural = "Historiques de statut de livraison"

    def __str__(self):
        return f"{self.delivery.reference} : {self.old_status} → {self.new_status}"


class DeliveryProof(models.Model):
    """Preuve de livraison (POD) — signature, photo, OTP, nom/téléphone du
    réceptionnaire, géolocalisation optionnelle (section 16)."""

    delivery = models.OneToOneField(Delivery, on_delete=models.CASCADE, related_name="proof")
    signature_image = models.ImageField(upload_to="deliveries/proofs/signatures/", blank=True, null=True)
    photo = models.ImageField(upload_to="deliveries/proofs/photos/", blank=True, null=True)
    otp_code = models.CharField(max_length=10, blank=True)
    receiver_name = models.CharField(max_length=150, blank=True)
    receiver_phone = models.CharField(max_length=30, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    confirmed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Preuve de livraison"
        verbose_name_plural = "Preuves de livraison"

    def __str__(self):
        return f"Preuve de livraison — {self.delivery.reference}"


class PricingRule(models.Model):
    """Règle de tarification additionnelle, cumulable avec la zone (Phase 2,
    section 13 — « tarification avancée multi-critères »). Chaque critère
    laissé vide s'applique à toutes les valeurs (ex : une règle sans
    `vehicle_type` s'applique quel que soit le véhicule). Toutes les règles
    dont les critères correspondent sont appliquées en cascade — transparent
    et prévisible plutôt qu'un système de priorité implicite."""

    zone = models.ForeignKey(DeliveryZone, on_delete=models.CASCADE, null=True, blank=True, related_name="pricing_rules", help_text="Laisser vide pour appliquer à toutes les zones.")
    vehicle_type = models.CharField(max_length=20, choices=Vehicle.VehicleType.choices, blank=True, help_text="Laisser vide pour tous les types de véhicule.")
    priority = models.CharField(max_length=20, choices=Delivery.Priority.choices, blank=True, help_text="Laisser vide pour toutes les priorités.")
    min_weight_kg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    max_weight_kg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    extra_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"), help_text="Montant fixe ajouté si la règle correspond.")
    multiplier_percent = models.IntegerField(default=0, help_text="Majoration en % du total courant si la règle correspond (peut être négatif).")
    label = models.CharField(max_length=150, help_text="Ex : Supplément camion hors zone")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Règle de tarification"
        verbose_name_plural = "Règles de tarification"

    def __str__(self):
        return self.label

    def matches(self, *, zone=None, vehicle_type="", priority="", weight_kg=None):
        if self.zone_id and (not zone or self.zone_id != zone.id):
            return False
        if self.vehicle_type and self.vehicle_type != vehicle_type:
            return False
        if self.priority and self.priority != priority:
            return False
        if self.min_weight_kg is not None and (weight_kg is None or weight_kg < self.min_weight_kg):
            return False
        if self.max_weight_kg is not None and (weight_kg is None or weight_kg > self.max_weight_kg):
            return False
        return True


class DeliveryReturn(models.Model):
    """Gestion des retours (Phase 2, section 17) — une livraison échouée ou
    refusée peut faire l'objet d'un retour tracé, avec motif et suivi du
    remboursement éventuel."""

    class Reason(models.TextChoices):
        REFUSED = "refused", "Refusé par le destinataire"
        DAMAGED = "damaged", "Colis endommagé"
        WRONG_ADDRESS = "wrong_address", "Adresse erronée"
        CLIENT_ABSENT = "client_absent", "Destinataire absent"
        OTHER = "other", "Autre"

    class RefundStatus(models.TextChoices):
        NONE = "none", "Aucun remboursement"
        PENDING = "pending", "Remboursement en attente"
        DONE = "done", "Remboursé"

    delivery = models.OneToOneField(Delivery, on_delete=models.CASCADE, related_name="return_record")
    reason = models.CharField(max_length=20, choices=Reason.choices)
    condition_notes = models.TextField(blank=True)
    refund_status = models.CharField(max_length=20, choices=RefundStatus.choices, default=RefundStatus.NONE)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Retour de livraison"
        verbose_name_plural = "Retours de livraison"

    def __str__(self):
        return f"Retour — {self.delivery.reference} ({self.get_reason_display()})"


class DeliveryExpense(models.Model):
    """Dépense liée au transport (Phase 2, section 19) — carburant, péage,
    entretien... rattachée à une livraison et/ou directement à un véhicule ou
    un transporteur (une dépense d'entretien n'est pas toujours liée à une
    livraison précise)."""

    class Category(models.TextChoices):
        FUEL = "fuel", "Carburant"
        TOLL = "toll", "Péage"
        MAINTENANCE = "maintenance", "Entretien"
        PARKING = "parking", "Stationnement"
        OTHER = "other", "Autre"

    delivery = models.ForeignKey(Delivery, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses")
    carrier = models.ForeignKey(Carrier, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.FUEL)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    expense_date = models.DateField(default=timezone.localdate)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-expense_date", "-id"]
        verbose_name = "Dépense transport"
        verbose_name_plural = "Dépenses transport"

    def __str__(self):
        return f"{self.get_category_display()} — {self.amount} XAF"
