from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.documents.validators import validate_image_file
from apps.providers.models import Provider


class MarketplaceType(models.TextChoices):
    SALE = "sale", "Marketplace vente"
    INTERIOR_DESIGN = "interior_design", "Décoration & design intérieur"
    ACTORS = "actors", "Marketplace des acteurs"
    VENUES = "venues", "Salles de réception"
    TALENT_MISSIONS = "talent_missions", "Missions pour talents"


class CommissionSettings(models.Model):
    """Taux de commission InnovEvent par marketplace — prélevé automatiquement
    sur chaque devis payé (section 23 du cahier des charges). Configurable par
    l'administration, sans déploiement : un taux par marketplace, avec valeur
    par défaut si aucun réglage spécifique n'existe."""

    marketplace_type = models.CharField(max_length=20, choices=MarketplaceType.choices, unique=True)
    commission_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("5.00"),
        help_text="Pourcentage prélevé par InnovEvent sur chaque paiement de devis dans ce marketplace.",
    )

    def __str__(self):
        return f"{self.get_marketplace_type_display()} — {self.commission_percent}%"


class SubscriptionTier(models.Model):
    """Palier d'abonnement (Free, Basic, Premium, Pro...) — architecture évolutive
    permettant de créer nouveaux paliers sans toucher au code : une fonctionnalité
    de marketplace peut exiger un palier minimum (`MarketplaceFeature.min_tier`)."""

    code = models.SlugField(max_length=30, unique=True)
    label = models.CharField(max_length=60)
    level = models.PositiveIntegerField(default=0, help_text="Plus élevé = plus de privilèges ; sert à comparer les paliers entre eux.")
    description = models.CharField(max_length=300, blank=True)
    is_default = models.BooleanField(default=False, help_text="Palier attribué par défaut à un nouvel abonnement.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "level"]

    def __str__(self):
        return self.label


class SubscriptionPlan(models.Model):
    """Formule de durée d'abonnement (1, 3, 6, 12 mois...) — même grille tarifaire
    pour tous les marketplaces premium. Entièrement gérée par l'administration
    (page « Paliers d'abonnement ») : aucun prix n'est plus codé en dur, afin de
    pouvoir ajuster la tarification sans déploiement."""

    code = models.SlugField(max_length=30, unique=True)
    label = models.CharField(max_length=60)
    months = models.PositiveIntegerField(default=1, help_text="Nombre de mois couverts par cette formule.")
    duration_days = models.PositiveIntegerField(help_text="Durée exacte en jours ajoutée à l'abonnement (permet un mois = 30 jours, etc.).")
    price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Prix total de la formule, en XAF.")
    discount_percent = models.PositiveSmallIntegerField(default=0, help_text="Purement informatif — affiché comme badge de réduction.")
    order = models.PositiveIntegerField(default=0)
    marketplace_type = models.CharField(max_length=30, choices=MarketplaceType.choices, null=True, blank=True, help_text="Vide = formule commune. Choisissez Missions pour talents pour son tarif dédié.")

    class Meta:
        ordering = ["order", "months"]

    def __str__(self):
        return f"{self.label} — {self.price} XAF"


class MarketplaceSubscription(models.Model):
    """Abonnement à UN marketplace précis (et non à l'ensemble) : un client paie
    pour consulter/acheter dans ce marketplace, un partenaire paie pour y publier
    son propre profil de prestataire. Même mécanisme des deux côtés — seule la
    conséquence (lecture vs. publication) diffère selon le rôle du compte."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="marketplace_subscriptions")
    marketplace_type = models.CharField(max_length=20, choices=MarketplaceType.choices)
    tier = models.ForeignKey(
        SubscriptionTier, on_delete=models.SET_NULL, null=True, blank=True, related_name="subscriptions",
        help_text="Palier souscrit — détermine l'accès aux fonctionnalités qui exigent un palier minimum.",
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "marketplace_type")]
        ordering = ["marketplace_type"]

    def __str__(self):
        return f"{self.user} — {self.get_marketplace_type_display()} (jusqu'au {self.expires_at:%d/%m/%Y})"

    def is_active(self):
        from django.utils import timezone

        return self.expires_at > timezone.now()


class MarketplaceListing(models.Model):
    """Service publié dans l'un des marketplaces premium, accessibles uniquement
    aux clients abonnés à CE marketplace précis : vente d'objets/équipements,
    décoration & design intérieur, ou prestations d'acteurs événementiels.
    Peut être créée par l'administration, ou par un partenaire (prestataire)
    ayant souscrit l'abonnement de publication pour ce marketplace — auquel cas
    `created_by` identifie son propriétaire. Peut aussi s'appuyer sur un
    prestataire déjà présent dans le catalogue (apps.providers)."""

    MarketplaceType = MarketplaceType

    marketplace_type = models.CharField(max_length=20, choices=MarketplaceType.choices)
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.SET_NULL, null=True, blank=True, related_name="marketplace_listings",
        help_text="Prestataire associé (optionnel) — réutilise sa fiche existante plutôt que de dupliquer l'information.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="marketplace_listings_owned",
        help_text="Partenaire propriétaire de cette annonce (vide si publiée directement par l'administration).",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="XAF")
    photo = models.ImageField(upload_to="marketplace/", blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Décocher pour masquer l'annonce sans la supprimer.")
    requires_subscription = models.BooleanField(
        default=True,
        help_text=(
            "Coché : visible uniquement par les comptes abonnés à ce marketplace précis. "
            "Décoché : accès libre, visible par tout client connecté (« mode client simple »)."
        ),
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["marketplace_type", "order", "-created_at"]

    def __str__(self):
        return f"[{self.get_marketplace_type_display()}] {self.title}"


class MarketplaceOrder(models.Model):
    """Commande d'un client sur un service publié dans un marketplace premium
    (paiement à l'unité, indépendant du prix de l'abonnement lui-même)."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        PAID = "paid", "Payée"
        FAILED = "failed", "Échouée"

    listing = models.ForeignKey(MarketplaceListing, on_delete=models.CASCADE, related_name="orders")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="marketplace_orders")
    payment = models.ForeignKey("payments.Payment", on_delete=models.SET_NULL, null=True, blank=True, related_name="marketplace_orders")
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.listing.title} — {self.buyer} ({self.get_status_display()})"


class ProfessionalProfile(models.Model):
    """Profil professionnel d'un partenaire (décorateur, DJ, wedding planner...),
    publié dans les marketplaces « Décoration & design intérieur » ou
    « Acteurs événementiels ». Un partenaire ne crée pas une boutique : il gère
    UN profil, qui peut ensuite proposer PLUSIEURS services (ProfessionalService)
    et une galerie de réalisations (ProfessionalPortfolioItem)."""

    class ClientType(models.TextChoices):
        INDIVIDUAL = "individual", "Particulier"
        PROFESSIONAL = "professional", "Professionnel"
        HOTEL_RESTAURANT = "hotel_restaurant", "Hôtel / Restaurant"

    class PriceRange(models.TextChoices):
        LOW = "€", "€ — Accessible"
        MID = "€€", "€€ — Intermédiaire"
        HIGH = "€€€", "€€€ — Haut de gamme"

    class VerificationStatus(models.TextChoices):
        NOT_VERIFIED = "not_verified", "Non vérifié"
        PROFILE_VERIFIED = "profile_verified", "Profil vérifié"
        IDENTITY_VERIFIED = "identity_verified", "Identité vérifiée"
        COMPANY_VERIFIED = "company_verified", "Entreprise vérifiée"
        PORTFOLIO_VERIFIED = "portfolio_verified", "Portfolio vérifié"
        PROFESSIONAL_PARTNER = "professional_partner", "Partenaire professionnel"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="professional_profile")
    marketplace_type = models.CharField(
        max_length=20,
        choices=[(MarketplaceType.INTERIOR_DESIGN, MarketplaceType.INTERIOR_DESIGN.label), (MarketplaceType.ACTORS, MarketplaceType.ACTORS.label)],
    )
    category = models.CharField(max_length=30, choices=Provider.Category.choices, blank=True)
    business_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    team_presentation = models.TextField(blank=True, help_text="Présentation de l'équipe")
    specialties = models.CharField(max_length=300, blank=True, help_text="Séparées par des virgules")
    country = models.CharField(
        max_length=2, default="CM",
        help_text="Code pays ISO 3166-1 alpha-2 (ex : CM). Préparé pour une expansion multi-pays future.",
    )
    city = models.CharField(max_length=100, blank=True)
    neighborhood = models.CharField(max_length=100, blank=True, help_text="Quartier")
    service_area = models.CharField(max_length=300, blank=True, help_text="Zone d'intervention (villes couvertes)")
    client_type = models.CharField(
        max_length=20, choices=ClientType.choices, blank=True,
        help_text="Type de clientèle desservie — filtre de la marketplace « Décoration & design intérieur ».",
    )
    price_range = models.CharField(
        max_length=3, choices=PriceRange.choices, blank=True,
        help_text="Gamme de prix indicative — filtre de la marketplace « Décoration & design intérieur ».",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Position de la ville principale (recherche « près de moi »)")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    max_distance_km = models.PositiveIntegerField(null=True, blank=True, help_text="Distance maximale d'intervention depuis la ville principale (km)")
    conditions = models.TextField(blank=True, help_text="Conditions générales de prestation")
    logo = models.ImageField(upload_to="marketplace/profiles/", blank=True, null=True, validators=[validate_image_file])
    cover_photo = models.ImageField(
        upload_to="marketplace/profiles/covers/", blank=True, null=True, validators=[validate_image_file],
    )
    id_card_photo = models.ImageField(
        upload_to="marketplace/profiles/id_cards/", blank=True, null=True, validators=[validate_image_file],
        help_text="Photo de la CNI — vérification d'identité, à fournir une fois lors de la création du profil.",
    )
    contact_phone = models.CharField(max_length=30, blank=True)
    contact_email = models.EmailField(blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    verification_status = models.CharField(
        max_length=25, choices=VerificationStatus.choices, default=VerificationStatus.NOT_VERIFIED,
        help_text="Statut de vérification, accordé par l'administration (section 6 du CDC).",
    )
    verification_requested_at = models.DateTimeField(null=True, blank=True)
    is_recommended = models.BooleanField(default=False, help_text="Badge « ★ Recommandé », accordé par l'administration.")
    is_top = models.BooleanField(default=False, help_text="Badge « 🏆 Top prestataire », accordé par l'administration.")
    completed_projects_count = models.PositiveIntegerField(default=0, help_text="Nombre de prestations réalisées (mis à jour manuellement en attendant le suivi automatique des réservations).")
    view_count = models.PositiveIntegerField(default=0, help_text="Nombre de consultations de la fiche (statistiques admin).")
    is_active = models.BooleanField(default=True, help_text="Décocher pour masquer le profil sans le supprimer.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.business_name} ({self.get_marketplace_type_display()})"

    def category_display(self):
        return dict(Provider.Category.choices).get(self.category, self.category)

    @property
    def is_verified(self):
        """Compatibilité ascendante : tout code qui lisait l'ancien booléen
        continue de fonctionner (« vérifié » = n'importe quel statut au-dessus
        de « non vérifié »), sans avoir à toucher chaque appelant."""
        return self.verification_status != self.VerificationStatus.NOT_VERIFIED

    def average_rating(self):
        from django.db.models import Avg

        return self.reviews.aggregate(avg=Avg("rating"))["avg"]

    def review_count(self):
        return self.reviews.count()


class ProfessionalService(models.Model):
    """Un service proposé par un profil professionnel — un profil peut en
    proposer plusieurs (ex: un décorateur propose « décoration de mariage » ET
    « décoration corporate », avec des tarifs et conditions différents)."""

    class PricingType(models.TextChoices):
        FIXED = "fixed", "Prix fixe"
        QUOTE = "quote", "Sur devis"

    profile = models.ForeignKey(ProfessionalProfile, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    pricing_type = models.CharField(max_length=10, choices=PricingType.choices, default=PricingType.QUOTE)
    price_from = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Prix à partir de (laisser vide si entièrement sur devis)")
    currency = models.CharField(max_length=3, default="XAF")
    duration_label = models.CharField(max_length=100, blank=True, help_text="Ex : 4 heures, 1 journée, week-end complet")
    capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Nombre de personnes incluses")
    conditions = models.CharField(max_length=300, blank=True, help_text="Conditions particulières à ce service")
    photo = models.ImageField(upload_to="marketplace/services/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.profile.business_name} — {self.name}"


class ProfessionalPortfolioItem(models.Model):
    """Photo de réalisation dans la galerie/portfolio d'un profil professionnel."""

    profile = models.ForeignKey(ProfessionalProfile, on_delete=models.CASCADE, related_name="portfolio_items")
    image = models.ImageField(upload_to="marketplace/portfolio/", help_text="Photo principale — ou photo « après » si un avant/après est renseigné.")
    before_image = models.ImageField(
        upload_to="marketplace/portfolio/before/", blank=True, null=True,
        help_text="Photo « avant » (optionnelle) — affichée en avant/après avec la photo principale.",
    )
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.profile.business_name} — {self.caption or 'photo'}"


class ProfessionalBookingRequest(models.Model):
    """Demande de devis d'un client abonné sur un profil professionnel — SANS
    jamais exposer les coordonnées personnelles du prestataire (téléphone,
    email, réseaux sociaux) au client sur la plateforme : le prestataire
    répond avec un devis structuré (voir `Quote`), entièrement au sein de
    l'application. L'administration garde une visibilité complète et peut
    intervenir à tout moment (statut, notes internes), mais n'est plus
    l'unique canal de réponse — le prestataire négocie désormais directement,
    via des objets métier, jamais via un contact direct hors plateforme."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente de réponse"
        QUOTED = "quoted", "Devis envoyé"
        MODIFICATION_REQUESTED = "modification_requested", "Modification demandée"
        ACCEPTED = "accepted", "Devis accepté — paiement attendu"
        CONFIRMED = "confirmed", "Confirmée (payée)"
        COMPLETED = "completed", "Prestation réalisée"
        DECLINED = "declined", "Refusée"
        CANCELLED = "cancelled", "Annulée"
        CONTACTED = "contacted", "Mise en relation effectuée (suivi manuel)"

    profile = models.ForeignKey(ProfessionalProfile, on_delete=models.CASCADE, related_name="booking_requests")
    service = models.ForeignKey(
        ProfessionalService, on_delete=models.SET_NULL, null=True, blank=True, related_name="booking_requests"
    )
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="professional_booking_requests")

    # --- Formulaire de demande de devis (section 12 du cahier des charges) ---
    event_type = models.CharField(max_length=120, blank=True, help_text="Ex : Mariage, Anniversaire, Séminaire d'entreprise")
    event_date = models.DateField(null=True, blank=True)
    event_time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, help_text="Lieu précis de l'événement")
    city = models.CharField(max_length=100, blank=True)
    guest_count = models.PositiveIntegerField(null=True, blank=True, help_text="Nombre de participants")
    budget_estimate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    options_wanted = models.TextField(blank=True, help_text="Options souhaitées par le client")
    contact_phone = models.CharField(max_length=30, blank=True, help_text="Numéro auquel joindre le client pour la mise en relation")
    message = models.TextField(blank=True, help_text="Description du besoin par le client")

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    admin_notes = models.TextField(blank=True, help_text="Notes internes de suivi — jamais visibles par le client ou le prestataire")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Demande #{self.pk} — {self.profile.business_name} ({self.get_status_display()})"

    @property
    def latest_quote(self):
        return self.quotes.order_by("-created_at").first()


class RequestedEquipmentItem(models.Model):
    """Matériel souhaité par le client au moment de sa demande de devis (ex :
    chaises, tables, projecteur, vaisselle...) — le prestataire connaît ainsi
    précisément le besoin matériel dès la demande, sans attendre un échange
    de messages séparé. Réutilise le catalogue matériel existant
    (apps.equipment) plutôt que du texte libre non exploitable."""

    booking_request = models.ForeignKey(
        ProfessionalBookingRequest, on_delete=models.CASCADE, related_name="requested_equipment",
    )
    equipment = models.ForeignKey("equipment.Equipment", on_delete=models.CASCADE, related_name="+")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.equipment.name} × {self.quantity}"


class Quote(models.Model):
    """Devis structuré envoyé par le prestataire en réponse à une demande —
    plusieurs versions possibles (une nouvelle ligne à chaque proposition),
    l'historique complet reste consultable. Jamais de coordonnées échangées
    ici : uniquement des lignes de prestation, prix et conditions."""

    class Status(models.TextChoices):
        SENT = "sent", "Envoyé"
        ACCEPTED = "accepted", "Accepté"
        DECLINED = "declined", "Refusé"
        MODIFICATION_REQUESTED = "modification_requested", "Modification demandée"
        EXPIRED = "expired", "Expiré"
        SUPERSEDED = "superseded", "Remplacé par une nouvelle version"

    booking_request = models.ForeignKey(ProfessionalBookingRequest, on_delete=models.CASCADE, related_name="quotes")
    travel_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    additional_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="XAF")
    conditions = models.TextField(blank=True, help_text="Conditions de prestation")
    cancellation_policy = models.TextField(blank=True, help_text="Conditions d'annulation")
    valid_until = models.DateField(null=True, blank=True, help_text="Date limite d'acceptation du devis")
    provider_note = models.TextField(blank=True, help_text="Message du prestataire accompagnant le devis (réponse à une question, précision...)")
    client_message = models.TextField(blank=True, help_text="Question ou demande de modification formulée par le client sur CE devis")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.SENT)
    payment = models.ForeignKey(
        "payments.Payment", on_delete=models.SET_NULL, null=True, blank=True, related_name="quotes"
    )
    # Calculés et figés au moment du paiement (jamais recalculés a posteriori,
    # même si le taux de commission change ensuite) — garantit une comptabilité
    # cohérente dans le temps.
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    provider_payout = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Devis #{self.pk} — {self.booking_request.profile.business_name} ({self.get_status_display()})"

    @property
    def items_total(self):
        return sum((item.line_total for item in self.items.all()), Decimal("0"))

    @property
    def total_amount(self):
        return self.items_total + self.travel_fee + self.additional_fees - self.discount


class QuoteLineItem(models.Model):
    """Une ligne de prestation dans un devis (ex : « Décoration de salle », 1 ×
    250 000 XAF)."""

    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="items")
    label = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.label} × {self.quantity}"


class MarketplaceFeature(models.Model):
    """Moteur central de permissions/visibilité : chaque bloc, bouton, section ou
    action des marketplaces premium est représenté ici par une entrée que
    l'administration peut activer/désactiver et reconfigurer SANS toucher au
    code. Une fonctionnalité désactivée n'est jamais supprimée : elle est
    seulement masquée de l'interface et redevient disponible en un clic."""

    class Visibility(models.TextChoices):
        EVERYONE = "everyone", "Tout le monde"
        AUTHENTICATED = "authenticated", "Utilisateurs connectés"
        NON_SUBSCRIBER = "non_subscriber", "Utilisateurs non abonnés"
        SUBSCRIBER = "subscriber", "Utilisateurs abonnés"
        ADMIN = "admin", "Administrateurs uniquement"

    class State(models.TextChoices):
        SHOWN = "shown", "Affiché"
        HIDDEN = "hidden", "Masqué"
        LOCKED = "locked", "Verrouillé"
        UPSELL = "upsell", "Affiché avec message d'abonnement"

    marketplace_type = models.CharField(max_length=20, choices=MarketplaceType.choices)
    key = models.SlugField(max_length=60, help_text="Identifiant technique stable, utilisé par le frontend (ex : book, contact, reviews).")
    label = models.CharField(max_length=120)
    description = models.CharField(max_length=300, blank=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.SUBSCRIBER)
    state = models.CharField(max_length=20, choices=State.choices, default=State.SHOWN)
    min_tier = models.ForeignKey(
        SubscriptionTier, on_delete=models.SET_NULL, null=True, blank=True, related_name="features",
        help_text="Palier minimum requis pour un utilisateur abonné (laisser vide = aucune exigence de palier).",
    )
    upsell_message = models.CharField(
        max_length=200, blank=True,
        help_text="Message affiché aux non-abonnés quand l'état est « Affiché avec message d'abonnement » ou « Verrouillé ».",
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("marketplace_type", "key")]
        ordering = ["marketplace_type", "order", "id"]

    def __str__(self):
        return f"{self.get_marketplace_type_display()} — {self.label}"


class ProfessionalAvailabilitySettings(models.Model):
    """Règles de disponibilité d'un prestataire — utilisées pour vérifier
    automatiquement les conflits avant qu'un client ne demande un devis."""

    profile = models.OneToOneField(ProfessionalProfile, on_delete=models.CASCADE, related_name="availability_settings")
    min_notice_days = models.PositiveIntegerField(default=2, help_text="Délai minimum, en jours, avant une date réservable.")
    max_bookings_per_day = models.PositiveIntegerField(default=1, help_text="Nombre maximum de prestations confirmées le même jour.")

    def __str__(self):
        return f"Disponibilités — {self.profile.business_name}"


class ProfessionalBlockedDate(models.Model):
    """Une date que le prestataire bloque manuellement (congé, déjà engagé
    ailleurs...), indépendamment des réservations confirmées sur la plateforme."""

    profile = models.ForeignKey(ProfessionalProfile, on_delete=models.CASCADE, related_name="blocked_dates")
    date = models.DateField()
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("profile", "date")]
        ordering = ["date"]

    def __str__(self):
        return f"{self.profile.business_name} — indisponible le {self.date:%d/%m/%Y}"


class ProfessionalFavorite(models.Model):
    """Un profil professionnel enregistré par un client abonné dans sa liste
    de favoris — purement personnel, jamais visible du prestataire ni des
    autres clients."""

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="professional_favorites")
    profile = models.ForeignKey(ProfessionalProfile, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("client", "profile")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.client} ♥ {self.profile.business_name}"
