from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.providers.models import Provider

from .models import (
    CommissionSettings,
    MarketplaceFeature,
    MarketplaceListing,
    MarketplaceOrder,
    MarketplaceSubscription,
    MarketplaceType,
    ProfessionalAvailabilitySettings,
    ProfessionalBlockedDate,
    ProfessionalBookingRequest,
    ProfessionalFavorite,
    ProfessionalPortfolioItem,
    ProfessionalProfile,
    ProfessionalService,
    Quote,
    QuoteLineItem,
    RequestedEquipmentItem,
    SubscriptionPlan,
    SubscriptionTier,
)


class MarketplaceListingSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source="provider.name", read_only=True, default=None)
    created_by_name = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = MarketplaceListing
        fields = [
            "id", "marketplace_type", "provider", "provider_name", "created_by", "created_by_name", "is_owner",
            "title", "description", "price", "currency", "photo", "is_active", "requires_subscription",
            "order", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username if obj.created_by else None

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.created_by_id == request.user.id)


class MarketplaceOrderSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    marketplace_type = serializers.CharField(source="listing.marketplace_type", read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = MarketplaceOrder
        fields = [
            "id", "listing", "listing_title", "marketplace_type", "buyer", "quantity",
            "status", "notes", "total_amount", "created_at",
        ]
        read_only_fields = ["id", "buyer", "status", "created_at"]

    def get_total_amount(self, obj):
        return obj.listing.price * obj.quantity


class MarketplaceOrderPaymentSerializer(serializers.Serializer):
    listing = serializers.PrimaryKeyRelatedField(queryset=MarketplaceListing.objects.filter(is_active=True))
    quantity = serializers.IntegerField(min_value=1, default=1)
    payment_provider = serializers.ChoiceField(choices=["demo", "paypal", "mobile_money", "freemopay", "kob"], default="demo")
    notes = serializers.CharField(required=False, allow_blank=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True)


class MarketplaceSubscriptionSerializer(serializers.ModelSerializer):
    marketplace_label = serializers.CharField(source="get_marketplace_type_display", read_only=True)
    is_active = serializers.SerializerMethodField()
    tier_label = serializers.CharField(source="tier.label", read_only=True, default=None)

    class Meta:
        model = MarketplaceSubscription
        fields = ["marketplace_type", "marketplace_label", "expires_at", "is_active", "tier", "tier_label"]

    def get_is_active(self, obj):
        return obj.is_active()


class SubscribeSerializer(serializers.Serializer):
    marketplace_type = serializers.ChoiceField(choices=MarketplaceType.choices)
    # Le code doit correspondre à un SubscriptionPlan existant (géré par
    # l'administration) — vérifié dans la vue, pas ici, pour ne jamais figer
    # la liste des formules possibles dans le code.
    plan = serializers.CharField(default="1_month")
    payment_provider = serializers.ChoiceField(
        choices=["demo", "mtn_momo", "orange_money", "card", "paypal", "mobile_money", "freemopay", "kob"],
        default="demo",
    )
    tier = serializers.PrimaryKeyRelatedField(queryset=SubscriptionTier.objects.all(), required=False, allow_null=True)


class ProfessionalServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalService
        fields = [
            "id", "profile", "name", "description", "pricing_type", "price_from", "currency",
            "duration_label", "capacity", "conditions", "photo", "is_active", "order",
        ]
        read_only_fields = ["id"]


class ProfessionalPortfolioItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalPortfolioItem
        fields = ["id", "profile", "image", "before_image", "caption", "order"]
        read_only_fields = ["id"]


class ProfessionalProfileSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(read_only=True)
    marketplace_label = serializers.CharField(source="get_marketplace_type_display", read_only=True)
    client_type_display = serializers.CharField(source="get_client_type_display", read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    services = ProfessionalServiceSerializer(many=True, read_only=True)
    portfolio_items = ProfessionalPortfolioItemSerializer(many=True, read_only=True)
    is_owner = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    verification_status_display = serializers.CharField(source="get_verification_status_display", read_only=True)

    class Meta:

        model = ProfessionalProfile
        fields = [
            "id", "user", "marketplace_type", "marketplace_label", "category", "category_display",
            "business_name", "description", "team_presentation", "specialties", "country",
            "city", "neighborhood", "service_area", "client_type", "client_type_display", "price_range",
            "latitude", "longitude", "max_distance_km", "conditions",
            "logo", "cover_photo", "id_card_photo", "contact_phone", "contact_email",
            "facebook_url", "instagram_url", "website_url",
            "is_verified", "verification_status", "verification_status_display", "verification_requested_at",
            "is_recommended", "is_top",
            "completed_projects_count", "view_count", "is_active",
            "average_rating", "review_count", "services", "portfolio_items", "is_owner", "is_favorited", "distance_km",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user", "is_verified", "verification_status", "verification_status_display", "verification_requested_at",
            "is_recommended", "is_top",
            "completed_projects_count", "view_count", "created_at", "updated_at",
        ]

    def get_distance_km(self, obj):
        value = getattr(obj, "distance_km", None)
        return round(value, 1) if value is not None else None

    def get_average_rating(self, obj):
        avg = obj.average_rating()
        return round(float(avg), 1) if avg is not None else None

    def get_review_count(self, obj):
        return obj.review_count()

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.user_id == request.user.id)

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        if not (request and request.user.is_authenticated):
            return False
        return obj.favorited_by.filter(client=request.user).exists()

    def to_representation(self, instance):
        """Le verrouillage fin (services, contenu détaillé...) est piloté par le
        même moteur de permissions que l'endpoint /features/resolve/ — jamais de
        condition codée en dur ici : on y consulte simplement le résultat. Le
        propriétaire et l'administration voient toujours tout."""
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = request.user if request else None
        is_privileged = bool(user and user.is_authenticated and (user.is_admin_role or instance.user_id == user.id))
        if is_privileged:
            data["features"] = []
            return data

        # La photo de CNI est une pièce d'identité — jamais exposée sur la
        # fiche publique, uniquement au titulaire du profil ou à l'administration
        # (couverts par le retour anticipé `is_privileged` ci-dessus).
        data.pop("id_card_photo", None)

        from .feature_engine import resolve_features

        features = resolve_features(user, instance.marketplace_type)
        data["features"] = features
        by_key = {f["key"]: f for f in features}

        view_profile = by_key.get("view_profile")
        if view_profile and (not view_profile["visible"] or view_profile["locked"]):
            for field in ("description", "team_presentation", "specialties", "conditions", "portfolio_items"):
                data[field] = [] if field == "portfolio_items" else ""

        view_services = by_key.get("view_services")
        if not view_services or not view_services["visible"] or view_services["locked"]:
            data["services"] = []

        return data


class ProfessionalProfileListSerializer(serializers.ModelSerializer):
    """Version allégée pour les listes (cartes de recherche) — sans services ni
    portfolio complets, pour limiter la charge utile."""

    category_display = serializers.CharField(read_only=True)
    marketplace_label = serializers.CharField(source="get_marketplace_type_display", read_only=True)
    client_type_display = serializers.CharField(source="get_client_type_display", read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    service_count = serializers.IntegerField(source="services.count", read_only=True)
    starting_price = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    verification_status_display = serializers.CharField(source="get_verification_status_display", read_only=True)

    class Meta:
        model = ProfessionalProfile
        fields = [
            "id", "marketplace_type", "marketplace_label", "category", "category_display",
            "business_name", "city", "neighborhood", "service_area", "client_type", "client_type_display", "price_range",
            "logo", "cover_photo", "is_verified", "verification_status", "verification_status_display",
            "is_recommended", "is_top",
            "average_rating", "review_count", "service_count", "starting_price", "is_owner", "is_favorited", "distance_km",
        ]

    def get_average_rating(self, obj):
        avg = obj.average_rating()
        return round(float(avg), 1) if avg is not None else None

    def get_review_count(self, obj):
        return obj.review_count()

    def get_distance_km(self, obj):
        value = getattr(obj, "distance_km", None)
        return round(value, 1) if value is not None else None

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.user_id == request.user.id)

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        if not (request and request.user.is_authenticated):
            return False
        favorited_ids = self.context.get("favorited_ids")
        if favorited_ids is not None:
            return obj.id in favorited_ids
        return obj.favorited_by.filter(client=request.user).exists()

    def get_starting_price(self, obj):
        prices = [s.price_from for s in obj.services.all() if s.is_active and s.price_from is not None]
        return min(prices) if prices else None


class QuoteLineItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = QuoteLineItem
        fields = ["id", "label", "quantity", "unit_price", "order", "line_total"]
        read_only_fields = ["id"]


class QuoteSerializer(serializers.ModelSerializer):
    """Devis structuré — la seule forme sous laquelle un prestataire répond à
    une demande : aucune coordonnée personnelle n'y transite, uniquement des
    lignes de prestation, un prix et des conditions."""

    items = QuoteLineItemSerializer(many=True)
    items_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Quote
        fields = [
            "id", "booking_request", "items", "items_total", "travel_fee", "additional_fees",
            "discount", "currency", "conditions", "cancellation_policy", "valid_until",
            "provider_note", "client_message", "status", "status_label", "total_amount",
            "commission_percent", "commission_amount", "provider_payout",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "client_message", "commission_percent", "commission_amount",
            "provider_payout", "created_at", "updated_at",
        ]

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Un devis doit contenir au moins une ligne de prestation.")
        return items

    def to_representation(self, instance):
        """La répartition commission/reversement n'est jamais montrée au
        client — seuls le prestataire concerné et l'administration la voient."""
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        is_privileged = bool(user and (user.is_admin_role or instance.booking_request.profile.user_id == user.id))
        if not is_privileged:
            data.pop("commission_percent", None)
            data.pop("commission_amount", None)
            data.pop("provider_payout", None)
        return data

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        quote = Quote.objects.create(**validated_data)
        for order, item in enumerate(items_data):
            QuoteLineItem.objects.create(quote=quote, order=order, **item)
        return quote


class RequestedEquipmentItemSerializer(serializers.ModelSerializer):
    equipment_name = serializers.CharField(source="equipment.name", read_only=True)
    equipment_photo = serializers.ImageField(source="equipment.photo", read_only=True)
    price_per_unit = serializers.DecimalField(source="equipment.price_per_unit", max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = RequestedEquipmentItem
        fields = ["id", "equipment", "equipment_name", "equipment_photo", "price_per_unit", "quantity"]
        read_only_fields = ["id"]


class ProfessionalBookingRequestSerializer(serializers.ModelSerializer):
    """Demande de devis — ne renvoie jamais les coordonnées personnelles direct
    du prestataire au client, ni celles du client au prestataire : toute la
    négociation passe par les devis structurés (`Quote`) ci-dessous."""

    business_name = serializers.CharField(source="profile.business_name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True, default=None)
    client_name = serializers.SerializerMethodField()
    client_phone = serializers.CharField(source="client.phone", read_only=True, default="")
    client_email = serializers.CharField(source="client.email", read_only=True, default="")
    latest_quote = serializers.SerializerMethodField()
    quotes = QuoteSerializer(many=True, read_only=True)
    requested_equipment = RequestedEquipmentItemSerializer(many=True, required=False)

    class Meta:
        model = ProfessionalBookingRequest
        fields = [
            "id", "profile", "business_name", "service", "service_name", "client", "client_name",
            "client_phone", "client_email", "event_type", "event_date", "event_time", "location", "city",
            "guest_count", "budget_estimate", "options_wanted", "contact_phone", "message",
            "requested_equipment", "status", "admin_notes", "latest_quote", "quotes", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "client", "status", "admin_notes", "created_at", "updated_at"]

    def get_client_name(self, obj):
        return obj.client.get_full_name() or obj.client.username

    def get_latest_quote(self, obj):
        quote = obj.latest_quote
        return QuoteSerializer(quote).data if quote else None

    def create(self, validated_data):
        items_data = validated_data.pop("requested_equipment", [])
        booking_request = ProfessionalBookingRequest.objects.create(**validated_data)
        for item in items_data:
            RequestedEquipmentItem.objects.create(booking_request=booking_request, **item)
        return booking_request

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Les coordonnées personnelles (client comme prestataire) ne circulent
        # jamais entre les deux parties — seule l'administration y a accès.
        # Le prestataire répond via un devis structuré, jamais par contact direct.
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        is_admin = bool(user and user.is_admin_role)
        is_client_author = bool(user and instance.client_id == user.id)
        if not is_admin:
            data.pop("client_phone", None)
            data.pop("client_email", None)
            if not is_client_author:
                data.pop("contact_phone", None)
        return data

    def validate(self, attrs):
        service = attrs.get("service")
        profile = attrs.get("profile") or getattr(self.instance, "profile", None)
        if service and profile and service.profile_id != profile.id:
            raise serializers.ValidationError({"service": "Ce service n'appartient pas à ce profil."})
        return attrs


class AdminBookingRequestUpdateSerializer(serializers.ModelSerializer):
    """Réservé à l'administration : seule habilitée à modifier librement le
    statut d'une demande et à y laisser des notes de suivi internes."""

    class Meta:
        model = ProfessionalBookingRequest
        fields = ["status", "admin_notes"]


class ProviderDeclineRequestSerializer(serializers.Serializer):
    """Le prestataire refuse directement une demande, sans envoyer de devis."""

    reason = serializers.CharField(required=False, allow_blank=True, max_length=300)


class ClientQuoteActionSerializer(serializers.Serializer):
    """Réponse du client à un devis reçu : accepter, refuser, ou demander une
    modification (avec message pour le prestataire)."""

    message = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class QuotePaymentSerializer(serializers.Serializer):
    payment_provider = serializers.ChoiceField(choices=["demo", "paypal", "mobile_money", "freemopay", "kob"], default="demo")
    coupon_code = serializers.CharField(required=False, allow_blank=True)


class SubscriptionTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionTier
        fields = ["id", "code", "label", "level", "description", "is_default", "order"]
        read_only_fields = ["id"]


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ["id", "code", "label", "months", "duration_days", "price", "discount_percent", "order", "marketplace_type"]
        read_only_fields = ["id"]


class CommissionSettingsSerializer(serializers.ModelSerializer):
    marketplace_label = serializers.CharField(source="get_marketplace_type_display", read_only=True)

    class Meta:
        model = CommissionSettings
        fields = ["id", "marketplace_type", "marketplace_label", "commission_percent"]
        read_only_fields = ["id"]


class MarketplaceFeatureSerializer(serializers.ModelSerializer):
    """Vue d'administration complète — toutes les fonctionnalités, quel que soit
    leur état, avec leurs libellés lisibles pour le tableau de gestion."""

    marketplace_label = serializers.CharField(source="get_marketplace_type_display", read_only=True)
    visibility_label = serializers.CharField(source="get_visibility_display", read_only=True)
    state_label = serializers.CharField(source="get_state_display", read_only=True)
    min_tier_label = serializers.CharField(source="min_tier.label", read_only=True, default=None)

    class Meta:
        model = MarketplaceFeature
        fields = [
            "id", "marketplace_type", "marketplace_label", "key", "label", "description",
            "visibility", "visibility_label", "state", "state_label",
            "min_tier", "min_tier_label", "upsell_message", "order",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ResolvedFeatureSerializer(serializers.Serializer):
    """Vue publique — ce que CET utilisateur peut effectivement voir/faire,
    consommée directement par le frontend (aucune fonctionnalité masquée n'y
    apparaît)."""

    key = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    visible = serializers.BooleanField()
    locked = serializers.BooleanField()
    upsell_message = serializers.CharField()


class ProfessionalProfileBadgesSerializer(serializers.ModelSerializer):
    """Réservé à l'administration : seule habilitée à accorder les badges de
    reconnaissance (section 17) et à faire progresser le statut de
    vérification (section 6 du cahier des charges)."""

    class Meta:
        model = ProfessionalProfile
        fields = ["verification_status", "is_recommended", "is_top"]


class AdminCreateProfileSerializer(serializers.Serializer):
    """Réservé à l'administration : ajoute directement une prestation dans une
    catégorie donnée, sans attendre qu'un prestataire s'inscrive lui-même —
    soit en la rattachant à un compte prestataire existant sans profil, soit
    en créant ce compte dans la foulée."""

    marketplace_type = serializers.ChoiceField(choices=MarketplaceType.choices)
    category = serializers.ChoiceField(choices=Provider.Category.choices)
    business_name = serializers.CharField(max_length=200)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    owner_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.filter(role=get_user_model().Role.PARTNER, professional_profile__isnull=True),
        required=False, allow_null=True,
    )
    new_owner_username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    new_owner_email = serializers.EmailField(required=False, allow_blank=True)
    new_owner_first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    new_owner_last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get("owner_user") and not attrs.get("new_owner_username"):
            raise serializers.ValidationError(
                "Choisissez un compte prestataire existant ou renseignez un identifiant pour en créer un nouveau."
            )
        return attrs


class ProfessionalAvailabilitySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalAvailabilitySettings
        fields = ["min_notice_days", "max_bookings_per_day"]


class ProfessionalBlockedDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalBlockedDate
        fields = ["id", "profile", "date", "reason", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProfessionalFavoriteSerializer(serializers.ModelSerializer):
    """Favoris du client — purement personnels, jamais visibles du prestataire."""

    profile_detail = ProfessionalProfileListSerializer(source="profile", read_only=True)

    class Meta:
        model = ProfessionalFavorite
        fields = ["id", "profile", "profile_detail", "created_at"]
        read_only_fields = ["id", "created_at"]
