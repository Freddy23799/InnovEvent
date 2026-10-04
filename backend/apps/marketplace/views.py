from collections import Counter
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db import models
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, Min, Q, Sum, Value
from django.db.models.functions import ACos, Cos, Greatest, Least, Radians, Sin
from django.http import FileResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin, IsAdminOrPublicReadOnly
from apps.messaging.models import Conversation
from apps.notifications.services import (
    notify_booking_request_contacted,
    notify_professional_booking_request_created,
    notify_professional_booking_request_status_changed,
    notify_quote_client_response,
    notify_quote_paid,
    notify_quote_sent,
)
from apps.payments.gateways import PaymentGatewayError, get_gateway
from apps.payments.models import Payment
from apps.referrals.services import apply_coupon, redeem_coupon

from .availability import get_availability_settings, resolve_month_availability
from .feature_engine import resolve_features
from .models import (
    CommissionSettings,
    MarketplaceFeature,
    MarketplaceListing,
    MarketplaceOrder,
    MarketplaceSubscription,
    MarketplaceType,
    ProfessionalBlockedDate,
    ProfessionalBookingRequest,
    ProfessionalFavorite,
    ProfessionalPortfolioItem,
    ProfessionalProfile,
    ProfessionalService,
    Quote,
    SubscriptionPlan,
    SubscriptionTier,
)
from .pdf import build_quote_pdf
from .serializers import (
    AdminBookingRequestUpdateSerializer,
    AdminCreateProfileSerializer,
    ClientQuoteActionSerializer,
    CommissionSettingsSerializer,
    MarketplaceFeatureSerializer,
    MarketplaceListingSerializer,
    MarketplaceOrderPaymentSerializer,
    MarketplaceOrderSerializer,
    MarketplaceSubscriptionSerializer,
    ProfessionalAvailabilitySettingsSerializer,
    ProfessionalBlockedDateSerializer,
    ProfessionalBookingRequestSerializer,
    ProfessionalFavoriteSerializer,
    ProfessionalPortfolioItemSerializer,
    ProfessionalProfileBadgesSerializer,
    ProfessionalProfileListSerializer,
    ProfessionalProfileSerializer,
    ProfessionalServiceSerializer,
    ProviderDeclineRequestSerializer,
    QuotePaymentSerializer,
    QuoteSerializer,
    ResolvedFeatureSerializer,
    SubscribeSerializer,
    SubscriptionPlanSerializer,
    SubscriptionTierSerializer,
)


def active_subscription_types(user):
    if not user.is_authenticated:
        return set()
    return set(
        MarketplaceSubscription.objects.filter(user=user, expires_at__gt=timezone.now())
        .values_list("marketplace_type", flat=True)
    )


def has_active_subscription(user, marketplace_type):
    return user.is_authenticated and MarketplaceSubscription.objects.filter(
        user=user, marketplace_type=marketplace_type, expires_at__gt=timezone.now()
    ).exists()


DEFAULT_COMMISSION_PERCENT = Decimal("5.00")


def get_commission_percent(marketplace_type):
    settings_row = CommissionSettings.objects.filter(marketplace_type=marketplace_type).first()
    return settings_row.commission_percent if settings_row else DEFAULT_COMMISSION_PERCENT


EARTH_RADIUS_KM = 6371

def distance_km_expression(from_lat, from_lng):
    """Distance à vol d'oiseau (formule de la loi des cosinus sphérique) entre
    un point fixe (le client) et la position enregistrée de chaque profil —
    calculée au niveau de la base pour permettre le tri et le filtrage sans
    charger tous les profils en mémoire. NULL pour un profil sans position
    renseignée (naturellement relégué en fin de tri)."""
    lat_rad = Radians(F("latitude"))
    lng_rad = Radians(F("longitude"))
    from_lat_rad = Radians(Value(from_lat))
    from_lng_rad = Radians(Value(from_lng))
    cos_angle = (
        Cos(from_lat_rad) * Cos(lat_rad) * Cos(lng_rad - from_lng_rad)
        + Sin(from_lat_rad) * Sin(lat_rad)
    )
    # Écarts flottants : l'argument de ACOS doit rester dans [-1, 1].
    clamped = Least(Value(1.0), Greatest(Value(-1.0), cos_angle))
    return ExpressionWrapper(ACos(clamped) * EARTH_RADIUS_KM, output_field=FloatField())


class CanManageOwnListing(permissions.BasePermission):
    """L'administration gère toutes les annonces ; un partenaire ne gère que
    celles dont il est propriétaire (`created_by`)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(user.is_admin_role or obj.created_by_id == user.id)


class MarketplaceListingViewSet(viewsets.ModelViewSet):
    """Annonces des marketplaces premium — chacune n'est visible qu'aux comptes
    abonnés à SON marketplace précis (ou à l'administration). Un partenaire peut
    publier sa propre annonce dans un marketplace auquel il est abonné ; il peut
    toujours gérer (modifier/masquer) la sienne même si l'abonnement a expiré,
    mais elle redevient alors invisible du public tant qu'il ne renouvelle pas."""

    serializer_class = MarketplaceListingSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["marketplace_type", "is_active"]

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), CanManageOwnListing()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = MarketplaceListing.objects.select_related("provider", "created_by")
        user = self.request.user
        if user.is_authenticated and user.is_admin_role:
            return qs
        # Accès libre (« mode client simple », ex. Marketplace vente) : visible par
        # tout client connecté sans abonnement. Sinon, seul un abonnement actif au
        # marketplace précis de l'annonce donne accès.
        free_access = Q(is_active=True, requires_subscription=False)
        subscribed = active_subscription_types(user)
        gated_access = Q(is_active=True, requires_subscription=True, marketplace_type__in=subscribed) if subscribed else Q(pk__in=[])
        visible = free_access | gated_access
        if self.action in ("retrieve", "update", "partial_update", "destroy") and user.is_authenticated:
            visible |= Q(created_by=user)
        return qs.filter(visible)

    def perform_create(self, serializer):
        user = self.request.user
        marketplace_type = serializer.validated_data["marketplace_type"]
        # `is_active` est forcé à True ici : DRF traite les requêtes multipart
        # (upload de photo) comme un formulaire HTML, où un booléen absent du
        # payload est interprété comme False plutôt que d'utiliser la valeur
        # par défaut du modèle — sans ce correctif, publier une photo à la
        # création masquerait silencieusement l'annonce.
        if user.is_admin_role:
            serializer.save(is_active=True)
            return
        if not has_active_subscription(user, marketplace_type):
            raise ValidationError({
                "marketplace_type": "Un abonnement actif à ce marketplace est requis pour y publier une annonce."
            })
        serializer.save(created_by=user, is_active=True)


class MarketplaceOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Historique des commandes passées sur les marketplaces premium."""

    serializer_class = MarketplaceOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = MarketplaceOrder.objects.select_related("listing", "buyer")
        if self.request.user.is_admin_role:
            return qs
        return qs.filter(buyer=self.request.user)


class MarketplaceOrderPaymentView(APIView):
    """Commande + paiement immédiat d'un service publié dans un marketplace
    premium — nécessite un abonnement actif au marketplace de CETTE annonce."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MarketplaceOrderPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        listing = data["listing"]

        needs_subscription = listing.requires_subscription and not request.user.is_admin_role
        if needs_subscription and not has_active_subscription(request.user, listing.marketplace_type):
            return Response(
                {"detail": "Un abonnement actif à ce marketplace est requis pour commander ce service."},
                status=status.HTTP_403_FORBIDDEN,
            )

        cost = listing.price * data["quantity"]
        coupon = None
        coupon_code = data.get("coupon_code")
        if coupon_code:
            context = {
                "marketplace_type": listing.marketplace_type,
                "category": listing.provider.category if listing.provider_id else "",
                "provider_id": listing.provider_id,
            }
            cost, _discount, coupon = apply_coupon(coupon_code, request.user, cost, context)

        payment = Payment.objects.create(
            user=request.user,
            amount=cost,
            currency=listing.currency,
            provider=data["payment_provider"],
            purpose="marketplace_order",
        )
        order = MarketplaceOrder.objects.create(
            listing=listing, buyer=request.user, payment=payment,
            quantity=data["quantity"], notes=data.get("notes", ""),
        )

        try:
            gateway = get_gateway(data["payment_provider"])
            success, provider_reference, raw_response = gateway.charge(payment)
        except PaymentGatewayError as exc:
            payment.status = Payment.Status.FAILED
            payment.failure_reason = str(exc)
            payment.save(update_fields=["status", "failure_reason"])
            order.status = MarketplaceOrder.Status.FAILED
            order.save(update_fields=["status"])
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        if not success:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])
            order.status = MarketplaceOrder.Status.FAILED
            order.save(update_fields=["status"])
            return Response({"detail": "Le paiement a échoué."}, status=status.HTTP_402_PAYMENT_REQUIRED)

        payment.status = Payment.Status.COMPLETED
        payment.provider_reference = provider_reference
        payment.raw_response = raw_response
        payment.completed_at = timezone.now()
        payment.save()

        if coupon:
            redeem_coupon(coupon, payment)

        order.status = MarketplaceOrder.Status.PAID
        order.save(update_fields=["status"])

        return Response(MarketplaceOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class MarketplaceSubscriptionView(APIView):
    """Abonnement à UN marketplace précis — l'abonné choisit lui-même sa formule
    (durée) parmi les `SubscriptionPlan` définis par l'administration (page
    « Paliers d'abonnement ») ; le tarif et la durée de CHAQUE formule ne sont
    jamais acceptés depuis le frontend, seul le CODE de la formule choisie
    l'est — le prix réel est relu en base au moment du paiement. Utilisé aussi
    bien par un client (pour consulter/acheter) que par un partenaire (pour y
    publier son propre profil de prestataire)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        subs = {s.marketplace_type: s for s in MarketplaceSubscription.objects.filter(user=request.user).select_related("tier")}
        marketplaces = []
        for value, label in MarketplaceListing.MarketplaceType.choices:
            sub = subs.get(value)
            marketplaces.append({
                "marketplace_type": value,
                "marketplace_label": label,
                "is_active": bool(sub and sub.is_active()),
                "expires_at": sub.expires_at if sub else None,
                "tier": sub.tier_id if sub else None,
                "tier_label": sub.tier.label if (sub and sub.tier) else None,
                "tier_level": sub.tier.level if (sub and sub.tier) else None,
            })
        requested_type = request.query_params.get("marketplace_type")
        plan_qs = SubscriptionPlan.objects.all()
        if requested_type:
            scoped = plan_qs.filter(marketplace_type=requested_type)
            plan_qs = scoped if scoped.exists() else plan_qs.filter(marketplace_type__isnull=True)
        else:
            plan_qs = plan_qs.filter(marketplace_type__isnull=True)
        plan_rows = list(plan_qs)
        plans = [{**SubscriptionPlanSerializer(p).data, "currency": "XAF"} for p in plan_rows]
        default_plan = plan_rows[0] if plan_rows else None
        tiers = SubscriptionTierSerializer(SubscriptionTier.objects.all(), many=True).data
        return Response({
            # Conservés pour compatibilité (formule la moins chère par défaut).
            "price": default_plan.price if default_plan else 0,
            "currency": "XAF",
            "duration_days": default_plan.duration_days if default_plan else 30,
            "plans": plans,
            "tiers": tiers,
            "marketplaces": marketplaces,
        })

    def post(self, request):
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        marketplace_type = serializer.validated_data["marketplace_type"]
        if marketplace_type == MarketplaceType.TALENT_MISSIONS:
            from apps.talents.models import TalentProfile
            if not TalentProfile.objects.filter(user=request.user, is_active=True).exists():
                return Response({"detail": "Un profil talent actif est requis pour cet abonnement."}, status=status.HTTP_403_FORBIDDEN)
        scoped_plans = SubscriptionPlan.objects.filter(marketplace_type=marketplace_type)
        plan_qs = scoped_plans if scoped_plans.exists() else SubscriptionPlan.objects.filter(marketplace_type__isnull=True)
        plan = plan_qs.filter(code=serializer.validated_data["plan"]).first()
        if not plan:
            return Response({"detail": "Formule d'abonnement inconnue."}, status=status.HTTP_400_BAD_REQUEST)
        provider = serializer.validated_data["payment_provider"]

        payment = Payment.objects.create(
            user=request.user,
            amount=plan.price,
            currency="XAF",
            provider=provider,
            purpose="marketplace_subscription",
        )

        try:
            gateway = get_gateway(provider)
            success, provider_reference, raw_response = gateway.charge(payment)
        except PaymentGatewayError as exc:
            payment.status = Payment.Status.FAILED
            payment.failure_reason = str(exc)
            payment.save(update_fields=["status", "failure_reason"])
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        if not success:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])
            return Response({"detail": "Le paiement a échoué."}, status=status.HTTP_402_PAYMENT_REQUIRED)

        payment.status = Payment.Status.COMPLETED
        payment.provider_reference = provider_reference
        payment.raw_response = raw_response
        payment.completed_at = timezone.now()
        payment.save()

        tier = serializer.validated_data.get("tier") or SubscriptionTier.objects.filter(is_default=True).first()

        sub, _ = MarketplaceSubscription.objects.get_or_create(
            user=request.user, marketplace_type=marketplace_type, defaults={"expires_at": timezone.now()}
        )
        base = sub.expires_at if sub.expires_at > timezone.now() else timezone.now()
        sub.expires_at = base + timezone.timedelta(days=plan.duration_days)
        sub.tier = tier
        sub.save(update_fields=["expires_at", "tier"])

        return Response(MarketplaceSubscriptionSerializer(sub).data)


class IsProfileOwnerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        profile = obj if isinstance(obj, ProfessionalProfile) else obj.profile
        return bool(request.user.is_admin_role or profile.user_id == request.user.id)


class ProfessionalProfileViewSet(viewsets.ModelViewSet):
    """Profil professionnel d'un partenaire (décorateur, DJ, wedding planner...) —
    consultable uniquement par les comptes abonnés au marketplace de CE profil
    (ou l'administration) ; un partenaire ne gère que son propre profil (un
    seul par compte)."""

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = [
        "marketplace_type", "category", "country", "city", "neighborhood", "verification_status", "client_type", "price_range",
    ]
    search_fields = ["business_name", "description", "specialties", "city", "neighborhood"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProfessionalProfileListSerializer
        return ProfessionalProfileSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if self.action == "list" and user.is_authenticated:
            # Évite une requête « is_favorited » par profil affiché : un seul
            # aller-retour pour toute la page de résultats.
            context["favorited_ids"] = set(
                ProfessionalFavorite.objects.filter(client=user).values_list("profile_id", flat=True)
            )
        return context

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsProfileOwnerOrAdmin()]
        if self.action in ("badges", "admin_create"):
            # Les badges de reconnaissance et l'ajout direct d'une prestation
            # ne sont accordés que par l'administration — jamais par un
            # prestataire, même sur son propre profil.
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def _apply_search_and_sort(self, qs):
        """Recherche avancée (section 7 du cahier des charges) : note minimum,
        géolocalisation et tri, en plus des filtres déjà gérés par
        DjangoFilterBackend/SearchFilter."""
        if self.action != "list":
            return qs
        params = self.request.query_params
        qs = qs.annotate(_avg_rating=Avg("reviews__rating"), _min_price=Min("services__price_from"))

        min_rating = params.get("min_rating")
        if min_rating:
            try:
                qs = qs.filter(_avg_rating__gte=float(min_rating))
            except ValueError:
                pass

        # Compatibilité : la case « vérifié uniquement » du frontend envoie un
        # simple booléen — `is_verified` n'étant plus un champ réel depuis le
        # passage à `verification_status` (section 6 du CDC), on traduit ici
        # plutôt que d'exiger un choix de palier précis à l'utilisateur.
        if params.get("is_verified") in ("true", "1"):
            qs = qs.exclude(verification_status=ProfessionalProfile.VerificationStatus.NOT_VERIFIED)

        # Disponibilité (section 8 du CDC) : exclut les profils ayant bloqué
        # cette date manuellement — même source de vérité que le calendrier
        # détaillé (`ProfessionalBlockedDate`, voir apps.marketplace.availability),
        # simplifiée pour un filtre de LISTE (sans la nuance de capacité
        # « FULL » par jour, propre au calendrier détail d'un seul profil).
        available_on = params.get("available_on")
        if available_on:
            try:
                target_date = date.fromisoformat(available_on)
            except ValueError:
                target_date = None
            if target_date:
                qs = qs.exclude(blocked_dates__date=target_date)

        near_lat, near_lng = params.get("near_lat"), params.get("near_lng")
        if near_lat and near_lng:
            try:
                qs = qs.annotate(distance_km=distance_km_expression(float(near_lat), float(near_lng)))
                max_distance = params.get("max_distance_km")
                if max_distance:
                    qs = qs.filter(distance_km__lte=float(max_distance))
            except (TypeError, ValueError):
                pass

        ordering_key = params.get("ordering")
        if ordering_key == "top_rated":
            qs = qs.order_by(F("_avg_rating").desc(nulls_last=True))
        elif ordering_key == "price_asc":
            qs = qs.order_by(F("_min_price").asc(nulls_last=True))
        elif ordering_key == "price_desc":
            qs = qs.order_by(F("_min_price").desc(nulls_last=True))
        elif ordering_key == "newest":
            qs = qs.order_by("-created_at")
        elif ordering_key == "nearest" and near_lat and near_lng:
            qs = qs.order_by(F("distance_km").asc(nulls_last=True))
        return qs

    def get_queryset(self):
        qs = ProfessionalProfile.objects.select_related("user").prefetch_related("services", "portfolio_items")
        user = self.request.user
        if user.is_authenticated and user.is_admin_role:
            return self._apply_search_and_sort(qs)

        # La liste ("Consulter les prestataires") est pilotée par le moteur de
        # permissions : si l'administration a rendu la fonctionnalité « browse »
        # visible aux non-abonnés pour ce marketplace, la liste (aperçu léger,
        # via ProfessionalProfileListSerializer) leur est ouverte — jamais la
        # fiche complète, qui reste gérée séparément ci-dessous.
        if self.action == "list":
            marketplace_type = self.request.query_params.get("marketplace_type")
            if marketplace_type and self._feature_visible(user, marketplace_type, "browse"):
                visible = Q(is_active=True, marketplace_type=marketplace_type)
                if user.is_authenticated:
                    visible |= Q(user=user)
                return self._apply_search_and_sort(qs.filter(visible))

        if self.action == "retrieve" and user.is_authenticated:
            # Le contrôle fin (visible mais verrouillé, avec message
            # d'abonnement) se fait dans retrieve() ci-dessous, une fois le
            # marketplace_type de CET objet connu ; ici on autorise seulement
            # la récupération de l'objet, pas encore son contenu détaillé.
            return qs.filter(Q(is_active=True) | Q(user=user))

        subscribed = active_subscription_types(user)
        visible = Q(is_active=True, marketplace_type__in=subscribed) if subscribed else Q(pk__in=[])
        if user.is_authenticated:
            visible |= Q(user=user)
        return self._apply_search_and_sort(qs.filter(visible))

    def _feature_visible(self, user, marketplace_type, key):
        feature = next((f for f in resolve_features(user, marketplace_type) if f["key"] == key), None)
        return bool(feature and feature["visible"])

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        is_privileged = user.is_admin_role or instance.user_id == user.id
        if not is_privileged and not self._feature_visible(user, instance.marketplace_type, "view_profile"):
            from django.http import Http404

            raise Http404
        if not is_privileged:
            # Statistique admin (« prestataires les plus consultés ») — jamais
            # comptée pour le propriétaire ou un administrateur qui consulte
            # sa propre gestion.
            ProfessionalProfile.objects.filter(pk=instance.pk).update(view_count=F("view_count") + 1)
            instance.view_count += 1
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def badges(self, request, pk=None):
        """Accorde ou retire les badges de reconnaissance — réservé à
        l'administration ; jamais accessible au prestataire lui-même."""
        if not request.user.is_admin_role:
            raise PermissionDenied("Seule l'administration peut accorder ou retirer un badge.")
        profile = self.get_object()
        serializer = ProfessionalProfileBadgesSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="admin-create")
    def admin_create(self, request):
        """Ajoute directement une prestation dans une catégorie donnée — sans
        attendre qu'un prestataire s'inscrive lui-même. Réservé à
        l'administration : rattache le profil à un compte prestataire existant
        sans profil, ou en crée un nouveau à la volée, et lui accorde
        immédiatement un abonnement actif pour que la prestation soit visible
        sans étape supplémentaire."""
        if not request.user.is_admin_role:
            raise PermissionDenied("Seule l'administration peut ajouter une prestation directement.")

        from django.contrib.auth import get_user_model

        User = get_user_model()
        serializer = AdminCreateProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        generated_password = None
        owner = data.get("owner_user")
        if not owner:
            username = data["new_owner_username"]
            if User.objects.filter(username=username).exists():
                raise ValidationError({"new_owner_username": "Cet identifiant est déjà utilisé."})
            owner = User.objects.create(
                username=username,
                email=data.get("new_owner_email", ""),
                first_name=data.get("new_owner_first_name", ""),
                last_name=data.get("new_owner_last_name", ""),
                role=User.Role.PARTNER,
                is_verified=True,
            )
            generated_password = User.objects.make_random_password()
            owner.set_password(generated_password)
            owner.save()
        elif hasattr(owner, "professional_profile"):
            raise ValidationError({"owner_user": "Ce compte a déjà un profil professionnel."})

        profile = ProfessionalProfile.objects.create(
            user=owner,
            marketplace_type=data["marketplace_type"],
            category=data["category"],
            business_name=data["business_name"],
            city=data.get("city", ""),
            description=data.get("description", ""),
            verification_status=ProfessionalProfile.VerificationStatus.PROFILE_VERIFIED,
            is_active=True,
        )
        default_tier = SubscriptionTier.objects.filter(is_default=True).first()
        MarketplaceSubscription.objects.update_or_create(
            user=owner, marketplace_type=data["marketplace_type"],
            defaults={"expires_at": timezone.now() + timedelta(days=365), "tier": default_tier},
        )

        response_data = ProfessionalProfileSerializer(profile, context=self.get_serializer_context()).data
        response_data["owner_username"] = owner.username
        if generated_password:
            response_data["generated_password"] = generated_password
        return Response(response_data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        user = self.request.user
        marketplace_type = serializer.validated_data["marketplace_type"]
        if hasattr(user, "professional_profile"):
            raise ValidationError({"detail": "Vous avez déjà un profil professionnel. Modifiez-le plutôt que d'en créer un nouveau."})
        if not user.is_admin_role and not has_active_subscription(user, marketplace_type):
            raise ValidationError({
                "marketplace_type": "Un abonnement actif à ce marketplace est requis pour publier un profil professionnel."
            })
        # Voir la note sur `is_active` dans MarketplaceListingViewSet.perform_create :
        # un upload de photo (multipart) à la création masquerait sinon le profil.
        serializer.save(user=user, is_active=True)

    @action(detail=True, methods=["get", "patch"], url_path="availability-settings")
    def availability_settings(self, request, pk=None):
        """Réglages de disponibilité du prestataire (délai minimum, nombre
        maximum de prestations par jour) — lecture/écriture réservées au
        propriétaire du profil (ou à l'administration)."""
        profile = self.get_object()
        if not (request.user.is_admin_role or profile.user_id == request.user.id):
            raise PermissionDenied("Seul le prestataire concerné peut consulter ou modifier ces réglages.")
        settings_obj = get_availability_settings(profile)
        if request.method == "GET":
            return Response(ProfessionalAvailabilitySettingsSerializer(settings_obj).data)
        serializer = ProfessionalAvailabilitySettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def availability(self, request, pk=None):
        """Disponibilités résolues pour un mois donné (?year=2026&month=12) —
        pilotée par le moteur de permissions comme tout le reste : si la
        fonctionnalité « availability_calendar » n'est pas visible pour cet
        utilisateur sur ce marketplace, l'action reste invisible."""
        profile = self.get_object()
        is_privileged = request.user.is_admin_role or profile.user_id == request.user.id
        if not is_privileged and not self._feature_visible(request.user, profile.marketplace_type, "availability_calendar"):
            raise PermissionDenied("Cette fonctionnalité n'est pas disponible pour votre compte.")
        try:
            year = int(request.query_params.get("year"))
            month = int(request.query_params.get("month"))
        except (TypeError, ValueError):
            today = timezone.now()
            year, month = today.year, today.month
        return Response(resolve_month_availability(profile, year, month))

    @action(detail=False, methods=["get"], url_path="recommended")
    def recommended(self, request):
        """Suggestions personnalisées (section « Recommandations intelligentes »
        du cahier des charges) : les catégories et la ville qui reviennent le
        plus souvent dans les favoris et demandes de devis du client
        déterminent les profils mis en avant, avec un bonus pour les badges et
        la note moyenne. Sans historique (« cold start »), on retombe
        simplement sur les profils les mieux notés / mis en avant par
        l'administration. Piloté par le moteur de permissions comme le reste
        (clé « recommendations »)."""
        user = request.user
        marketplace_type = request.query_params.get("marketplace_type")
        if not marketplace_type:
            raise ValidationError({"marketplace_type": "Ce paramètre est requis."})
        if not (user.is_admin_role or self._feature_visible(user, marketplace_type, "recommendations")):
            raise PermissionDenied("Cette fonctionnalité n'est pas disponible pour votre compte.")

        try:
            limit = min(max(int(request.query_params.get("limit", 8)), 1), 20)
        except ValueError:
            limit = 8

        favorited_ids = set(
            ProfessionalFavorite.objects.filter(client=user, profile__marketplace_type=marketplace_type)
            .values_list("profile_id", flat=True)
        )
        booking_qs = ProfessionalBookingRequest.objects.filter(client=user, profile__marketplace_type=marketplace_type)
        booked_ids = set(booking_qs.values_list("profile_id", flat=True))
        known_ids = favorited_ids | booked_ids

        preferred_categories = Counter(
            ProfessionalProfile.objects.filter(pk__in=known_ids).exclude(category="").values_list("category", flat=True)
        )
        preferred_cities = Counter(
            city for city in booking_qs.exclude(city="").values_list("city", flat=True) if city
        )
        top_categories = {category for category, _ in preferred_categories.most_common(3)}
        top_city = preferred_cities.most_common(1)[0][0] if preferred_cities else None

        candidates = (
            ProfessionalProfile.objects.filter(is_active=True, marketplace_type=marketplace_type)
            .exclude(pk__in=known_ids)
            .exclude(user_id=user.id)
            .select_related("user")
            .prefetch_related("services")
            .annotate(_avg_rating=Avg("reviews__rating"))
        )

        def score(profile):
            value = 0.0
            if profile.category in top_categories:
                value += 5
            if top_city and profile.city == top_city:
                value += 3
            if profile.is_recommended:
                value += 2
            if profile.is_top:
                value += 2
            if profile.is_verified:
                value += 1
            if profile._avg_rating:
                value += float(profile._avg_rating)
            return value

        ranked = sorted(candidates, key=score, reverse=True)[:limit]
        serializer = ProfessionalProfileListSerializer(ranked, many=True, context=self.get_serializer_context())
        return Response(serializer.data)


class ProfessionalServiceViewSet(viewsets.ModelViewSet):
    """Services proposés par un profil professionnel — un profil peut en
    publier plusieurs (section « services proposés » du cahier des charges)."""

    serializer_class = ProfessionalServiceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["profile", "is_active"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsProfileOwnerOrAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = ProfessionalService.objects.select_related("profile")
        user = self.request.user
        if user.is_authenticated and user.is_admin_role:
            return qs
        subscribed = active_subscription_types(user)
        visible = Q(is_active=True, profile__is_active=True, profile__marketplace_type__in=subscribed) if subscribed else Q(pk__in=[])
        if user.is_authenticated:
            visible |= Q(profile__user=user)
        return qs.filter(visible)

    def perform_create(self, serializer):
        profile = serializer.validated_data["profile"]
        if not (self.request.user.is_admin_role or profile.user_id == self.request.user.id):
            raise ValidationError({"detail": "Vous ne pouvez ajouter un service qu'à votre propre profil."})
        # Voir la note sur `is_active` dans MarketplaceListingViewSet.perform_create.
        serializer.save(is_active=True)


class ProfessionalPortfolioItemViewSet(viewsets.ModelViewSet):
    """Galerie de réalisations d'un profil professionnel."""

    serializer_class = ProfessionalPortfolioItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["profile"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsProfileOwnerOrAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = ProfessionalPortfolioItem.objects.select_related("profile")
        user = self.request.user
        if user.is_authenticated and user.is_admin_role:
            return qs
        subscribed = active_subscription_types(user)
        visible = Q(profile__is_active=True, profile__marketplace_type__in=subscribed) if subscribed else Q(pk__in=[])
        if user.is_authenticated:
            visible |= Q(profile__user=user)
        return qs.filter(visible)

    def perform_create(self, serializer):
        profile = serializer.validated_data["profile"]
        if not (self.request.user.is_admin_role or profile.user_id == self.request.user.id):
            raise ValidationError({"detail": "Vous ne pouvez ajouter une photo qu'à votre propre portfolio."})
        serializer.save()


class ProfessionalBlockedDateViewSet(viewsets.ModelViewSet):
    """Dates bloquées manuellement par un prestataire (congé, déjà engagé
    ailleurs...) — gérées uniquement par le propriétaire du profil (ou
    l'administration) ; jamais consultées publiquement telles quelles, voir
    `ProfessionalProfileViewSet.availability` pour la vue résolue."""

    serializer_class = ProfessionalBlockedDateSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfileOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["profile"]
    pagination_class = None

    def get_queryset(self):
        qs = ProfessionalBlockedDate.objects.select_related("profile")
        user = self.request.user
        if user.is_admin_role:
            return qs
        return qs.filter(profile__user=user)

    def perform_create(self, serializer):
        profile = serializer.validated_data["profile"]
        if not (self.request.user.is_admin_role or profile.user_id == self.request.user.id):
            raise ValidationError({"detail": "Vous ne pouvez bloquer des dates que sur votre propre profil."})
        serializer.save()


class ProfessionalFavoriteViewSet(viewsets.ModelViewSet):
    """Liste de favoris d'un client — purement personnelle : jamais visible
    du prestataire, ni des autres clients, ni de l'administration au-delà du
    strict nécessaire pour le support."""

    serializer_class = ProfessionalFavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]
    pagination_class = None

    def get_queryset(self):
        return ProfessionalFavorite.objects.filter(client=self.request.user).select_related("profile").prefetch_related(
            "profile__services"
        )

    def perform_create(self, serializer):
        profile = serializer.validated_data["profile"]
        user = self.request.user
        if not (user.is_admin_role or self._feature_visible(user, profile.marketplace_type, "favorites")):
            raise ValidationError({"detail": "Un abonnement actif à ce marketplace est requis pour ajouter des favoris."})
        try:
            serializer.save(client=user)
        except IntegrityError:
            raise ValidationError({"detail": "Ce profil est déjà dans vos favoris."})

    def _feature_visible(self, user, marketplace_type, key):
        feature = next((f for f in resolve_features(user, marketplace_type) if f["key"] == key), None)
        return bool(feature and feature["visible"])

    @action(detail=False, methods=["delete"], url_path=r"by-profile/(?P<profile_id>[^/.]+)")
    def by_profile(self, request, profile_id=None):
        """Retire un favori en connaissant seulement l'id du profil (pratique
        pour un bouton « cœur » qui ne connaît pas l'id de l'entrée favori)."""
        deleted, _ = ProfessionalFavorite.objects.filter(client=request.user, profile_id=profile_id).delete()
        if not deleted:
            return Response({"detail": "Ce profil n'est pas dans vos favoris."}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfessionalBookingRequestViewSet(viewsets.ModelViewSet):
    """Demande de devis sur un profil professionnel — le prestataire y répond
    directement par un devis structuré (voir `QuoteViewSet`), jamais par un
    contact personnel direct ; l'administration garde une visibilité et un
    droit d'intervention complets sur le statut."""

    http_method_names = ["get", "post", "patch", "head", "options"]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["profile", "status"]

    def get_serializer_class(self):
        user = self.request.user
        if self.action in ("update", "partial_update") and user.is_authenticated and user.is_admin_role:
            return AdminBookingRequestUpdateSerializer
        if self.action == "decline":
            return ProviderDeclineRequestSerializer
        return ProfessionalBookingRequestSerializer

    def get_permissions(self):
        if self.action in ("update", "partial_update"):
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = ProfessionalBookingRequest.objects.select_related("profile", "service", "client").prefetch_related("quotes__items")
        user = self.request.user
        if user.is_admin_role:
            return qs
        return qs.filter(Q(client=user) | Q(profile__user=user))

    def perform_create(self, serializer):
        user = self.request.user
        profile = serializer.validated_data["profile"]
        if not profile.is_active:
            raise ValidationError({"detail": "Ce profil n'est plus disponible."})
        if not user.is_admin_role and not has_active_subscription(user, profile.marketplace_type):
            raise ValidationError({
                "detail": "Un abonnement actif à ce marketplace est requis pour demander un devis."
            })
        booking_request = serializer.save(client=user)
        notify_professional_booking_request_created(booking_request)

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        booking_request = serializer.save()
        if booking_request.status != old_status:
            if booking_request.status == ProfessionalBookingRequest.Status.CONTACTED:
                # Validation admin de la mise en relation : ouvre directement la
                # messagerie entre le client et le prestataire plutôt que de se
                # contenter d'un statut informatif — voir notify_booking_request_contacted.
                conversation = Conversation.get_or_create_between(booking_request.client, booking_request.profile.user)
                notify_booking_request_contacted(booking_request, conversation)
            else:
                notify_professional_booking_request_status_changed(booking_request)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        """Le prestataire refuse directement la demande, sans envoyer de devis."""
        booking_request = self.get_object()
        if not (request.user.is_admin_role or booking_request.profile.user_id == request.user.id):
            raise PermissionDenied("Seul le prestataire concerné (ou l'administration) peut refuser cette demande.")
        if booking_request.status not in (
            ProfessionalBookingRequest.Status.PENDING, ProfessionalBookingRequest.Status.MODIFICATION_REQUESTED,
        ):
            raise ValidationError({"detail": "Cette demande ne peut plus être refusée directement."})
        serializer = ProviderDeclineRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")
        booking_request.status = ProfessionalBookingRequest.Status.DECLINED
        if reason:
            booking_request.admin_notes = (booking_request.admin_notes + f"\nRefus prestataire : {reason}").strip()
        booking_request.save(update_fields=["status", "admin_notes", "updated_at"])
        notify_professional_booking_request_status_changed(booking_request)
        return Response(ProfessionalBookingRequestSerializer(booking_request, context={"request": request}).data)


class QuoteViewSet(viewsets.ModelViewSet):
    """Devis structuré envoyé par un prestataire en réponse à une demande —
    seule forme de réponse possible : jamais de coordonnée personnelle
    échangée, uniquement des lignes de prestation, un prix et des conditions.
    Le client répond ensuite via les actions accept/decline/request_modification,
    jusqu'au paiement qui confirme la réservation."""

    http_method_names = ["get", "post", "head", "options"]
    serializer_class = QuoteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["booking_request", "status"]

    def get_queryset(self):
        qs = Quote.objects.select_related("booking_request__profile__user", "booking_request__client").prefetch_related("items")
        user = self.request.user
        if user.is_admin_role:
            return qs
        return qs.filter(Q(booking_request__client=user) | Q(booking_request__profile__user=user))

    def perform_create(self, serializer):
        user = self.request.user
        booking_request = serializer.validated_data["booking_request"]
        if not (user.is_admin_role or booking_request.profile.user_id == user.id):
            raise PermissionDenied("Seul le prestataire concerné peut envoyer un devis pour cette demande.")
        if booking_request.status not in (
            ProfessionalBookingRequest.Status.PENDING,
            ProfessionalBookingRequest.Status.QUOTED,
            ProfessionalBookingRequest.Status.MODIFICATION_REQUESTED,
        ):
            raise ValidationError({"detail": "Cette demande n'accepte plus de nouveau devis."})

        # Une nouvelle proposition remplace les précédentes, dont l'historique reste consultable.
        booking_request.quotes.filter(
            status__in=[Quote.Status.SENT, Quote.Status.MODIFICATION_REQUESTED]
        ).update(status=Quote.Status.SUPERSEDED)

        quote = serializer.save()
        booking_request.status = ProfessionalBookingRequest.Status.QUOTED
        booking_request.save(update_fields=["status", "updated_at"])
        notify_quote_sent(quote)

    def _client_only(self, quote, request):
        if not (request.user.is_admin_role or quote.booking_request.client_id == request.user.id):
            raise PermissionDenied("Seul le client à l'origine de la demande peut effectuer cette action.")

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        quote = self.get_object()
        self._client_only(quote, request)
        if quote.status != Quote.Status.SENT:
            raise ValidationError({"detail": "Ce devis n'est plus en attente de réponse."})
        quote.status = Quote.Status.ACCEPTED
        quote.save(update_fields=["status", "updated_at"])
        quote.booking_request.status = ProfessionalBookingRequest.Status.ACCEPTED
        quote.booking_request.save(update_fields=["status", "updated_at"])
        notify_quote_client_response(quote)
        return Response(QuoteSerializer(quote).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        quote = self.get_object()
        self._client_only(quote, request)
        if quote.status != Quote.Status.SENT:
            raise ValidationError({"detail": "Ce devis n'est plus en attente de réponse."})
        quote.status = Quote.Status.DECLINED
        quote.save(update_fields=["status", "updated_at"])
        quote.booking_request.status = ProfessionalBookingRequest.Status.DECLINED
        quote.booking_request.save(update_fields=["status", "updated_at"])
        notify_quote_client_response(quote)
        return Response(QuoteSerializer(quote).data)

    @action(detail=True, methods=["post"], url_path="request-modification")
    def request_modification(self, request, pk=None):
        quote = self.get_object()
        self._client_only(quote, request)
        if quote.status != Quote.Status.SENT:
            raise ValidationError({"detail": "Ce devis n'est plus en attente de réponse."})
        serializer = ClientQuoteActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quote.status = Quote.Status.MODIFICATION_REQUESTED
        quote.client_message = serializer.validated_data.get("message", "")
        quote.save(update_fields=["status", "client_message", "updated_at"])
        quote.booking_request.status = ProfessionalBookingRequest.Status.MODIFICATION_REQUESTED
        quote.booking_request.save(update_fields=["status", "updated_at"])
        notify_quote_client_response(quote)
        return Response(QuoteSerializer(quote).data)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        quote = self.get_object()
        self._client_only(quote, request)
        quote_pk = quote.pk

        serializer = QuotePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = serializer.validated_data["payment_provider"]
        coupon_code = serializer.validated_data.get("coupon_code")

        # Transaction + verrou de ligne : sans cela, deux appels `pay`
        # concurrents sur le même devis pouvaient tous deux passer le contrôle
        # « pas déjà payé » et créer deux paiements réels pour un seul devis
        # (même raisonnement que `BookingViewSet.pay`).
        with transaction.atomic():
            # `of=("self",)` + pas de select_related sur `payment` (nullable,
            # modifié par cette opération elle-même) : Postgres refuse FOR
            # UPDATE traversant une jointure externe vers une colonne
            # nullable, et une jointure « figée avant l'attente » sur une
            # ligne concurrente donnerait un `quote.payment` obsolète une fois
            # le verrou débloqué (voir le même correctif détaillé sur
            # `BookingViewSet.pay`). `booking_request`/`profile` restent en
            # select_related : jamais modifiés par cette méthode, donc aucun
            # risque de lecture obsolète.
            quote = Quote.objects.select_for_update(of=("self",)).select_related(
                "booking_request", "booking_request__profile",
            ).get(pk=quote_pk)

            if quote.status != Quote.Status.ACCEPTED:
                raise ValidationError({"detail": "Ce devis doit être accepté avant paiement."})
            if quote.payment_id and quote.payment.status == Payment.Status.COMPLETED:
                raise ValidationError({"detail": "Ce devis a déjà été payé."})

            amount = quote.total_amount
            coupon = None
            if coupon_code:
                profile = quote.booking_request.profile
                context = {
                    "marketplace_type": profile.marketplace_type, "category": profile.category,
                    "professional_profile_id": profile.id, "service_id": quote.booking_request.service_id,
                }
                amount, _discount, coupon = apply_coupon(coupon_code, request.user, amount, context)

            payment = Payment.objects.create(
                user=request.user, amount=amount, currency=quote.currency,
                provider=provider, purpose="marketplace_quote",
            )
            try:
                gateway = get_gateway(provider)
                success, provider_reference, raw_response = gateway.charge(payment)
            except PaymentGatewayError as exc:
                payment.status = Payment.Status.FAILED
                payment.failure_reason = str(exc)
                payment.save(update_fields=["status", "failure_reason"])
                return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

            if not success:
                payment.status = Payment.Status.FAILED
                payment.save(update_fields=["status"])
                return Response({"detail": "Le paiement a échoué."}, status=status.HTTP_402_PAYMENT_REQUIRED)

            payment.status = Payment.Status.COMPLETED
            payment.provider_reference = provider_reference
            payment.raw_response = raw_response
            payment.completed_at = timezone.now()
            payment.save()

            if coupon:
                redeem_coupon(coupon, payment)

            # Commission figée au moment du paiement — jamais recalculée si le taux
            # change ensuite, pour garder une comptabilité cohérente dans le temps.
            # Basée sur `quote.total_amount` (valeur pleine), pas sur `amount` déjà
            # réduit par un coupon éventuel : la réduction de parrainage est portée
            # par la plateforme, jamais déduite du montant reversé au prestataire.
            commission_percent = get_commission_percent(quote.booking_request.profile.marketplace_type)
            commission_amount = (quote.total_amount * commission_percent / Decimal("100")).quantize(Decimal("0.01"))
            quote.payment = payment
            quote.commission_percent = commission_percent
            quote.commission_amount = commission_amount
            quote.provider_payout = quote.total_amount - commission_amount
            quote.save(update_fields=["payment", "commission_percent", "commission_amount", "provider_payout", "updated_at"])
            quote.booking_request.status = ProfessionalBookingRequest.Status.CONFIRMED
            quote.booking_request.save(update_fields=["status", "updated_at"])
        notify_quote_paid(quote)
        return Response(QuoteSerializer(quote).data)

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        quote = self.get_object()
        pdf_bytes = build_quote_pdf(quote)
        from io import BytesIO

        return FileResponse(
            BytesIO(pdf_bytes), as_attachment=True, filename=f"devis-{quote.pk:06d}.pdf", content_type="application/pdf",
        )


class SubscriptionTierViewSet(viewsets.ModelViewSet):
    """Paliers d'abonnement (Free, Basic, Premium, Pro...) — lecture publique
    (utile pour afficher les options au moment de s'abonner), gestion réservée
    à l'administration."""

    queryset = SubscriptionTier.objects.all()
    serializer_class = SubscriptionTierSerializer
    permission_classes = [IsAdminOrPublicReadOnly]
    pagination_class = None


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    """Formules de durée d'abonnement (1, 3, 6, 12 mois...) et leur tarif — lecture
    publique (page de souscription), tarification modifiable uniquement par
    l'administration (page « Paliers d'abonnement »)."""

    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAdminOrPublicReadOnly]
    pagination_class = None


class CommissionSettingsViewSet(viewsets.ModelViewSet):
    """Taux de commission par marketplace — lecture réservée à l'administration
    (jamais exposée au client ni au prestataire, qui ne voient que le montant
    net de leur devis)."""

    queryset = CommissionSettings.objects.all()
    serializer_class = CommissionSettingsSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    pagination_class = None


class MarketplaceFeatureViewSet(viewsets.ModelViewSet):
    """Panneau d'administration du moteur de permissions : liste ET gère TOUTES
    les fonctionnalités de marketplace, quel que soit leur état (y compris
    masquées), afin que l'administration puisse les retrouver et les
    réactiver. Jamais consommé directement par l'interface publique — voir
    `MarketplaceFeatureResolveView` pour la vue résolue par utilisateur."""

    queryset = MarketplaceFeature.objects.select_related("min_tier")
    serializer_class = MarketplaceFeatureSerializer
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["marketplace_type", "state", "visibility"]
    pagination_class = None


class MarketplaceAnalyticsView(APIView):
    """Tableau de bord admin (section 22 du cahier des charges) : vue
    d'ensemble de l'activité des marketplaces premium — un seul appel agrège
    tout ce qui serait autrement dispersé entre plusieurs écrans."""

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        now = timezone.now()

        active_subs = MarketplaceSubscription.objects.filter(expires_at__gt=now)
        expired_subs = MarketplaceSubscription.objects.filter(expires_at__lte=now)

        revenue_by_purpose = {
            row["purpose"]: row["total"]
            for row in Payment.objects.filter(status=Payment.Status.COMPLETED, purpose__startswith="marketplace_")
            .values("purpose").annotate(total=Sum("amount"))
        }
        total_revenue = sum(revenue_by_purpose.values()) or 0

        most_viewed = ProfessionalProfile.objects.filter(is_active=True).order_by("-view_count")[:5]
        most_booked = (
            ProfessionalProfile.objects.filter(is_active=True)
            .annotate(confirmed_count=Count(
                "booking_requests", filter=Q(booking_requests__status=ProfessionalBookingRequest.Status.CONFIRMED)
            ))
            .order_by("-confirmed_count")[:5]
        )
        most_requested_services = (
            ProfessionalService.objects.filter(is_active=True).select_related("profile")
            .annotate(request_count=Count("booking_requests"))
            .order_by("-request_count")[:5]
        )
        top_cities = (
            ProfessionalBookingRequest.objects.exclude(city="")
            .values("city").annotate(count=Count("id")).order_by("-count")[:5]
        )

        paid_quotes = Quote.objects.filter(commission_amount__isnull=False)
        commission_totals = paid_quotes.aggregate(
            commission=Sum("commission_amount"), payouts=Sum("provider_payout"),
        )

        return Response({
            "clients_count": User.objects.filter(role=User.Role.CLIENT).count(),
            "providers_count": ProfessionalProfile.objects.count(),
            "active_subscriptions_count": active_subs.count(),
            "expired_subscriptions_count": expired_subs.count(),
            "quote_requests_count": ProfessionalBookingRequest.objects.count(),
            "confirmed_bookings_count": ProfessionalBookingRequest.objects.filter(
                status=ProfessionalBookingRequest.Status.CONFIRMED
            ).count(),
            "revenue": {
                "total": total_revenue,
                "subscriptions": revenue_by_purpose.get("marketplace_subscription", 0),
                "quotes": revenue_by_purpose.get("marketplace_quote", 0),
                "orders": revenue_by_purpose.get("marketplace_order", 0),
                "currency": "XAF",
            },
            "commission": {
                "total_commission": commission_totals["commission"] or 0,
                "total_provider_payouts": commission_totals["payouts"] or 0,
                "paid_quotes_count": paid_quotes.count(),
                "currency": "XAF",
            },
            "most_viewed_profiles": [
                {"id": p.id, "business_name": p.business_name, "view_count": p.view_count} for p in most_viewed
            ],
            "most_booked_profiles": [
                {"id": p.id, "business_name": p.business_name, "confirmed_count": p.confirmed_count} for p in most_booked
            ],
            "most_requested_services": [
                {"id": s.id, "name": s.name, "business_name": s.profile.business_name, "request_count": s.request_count}
                for s in most_requested_services
            ],
            "top_cities": [{"city": row["city"], "count": row["count"]} for row in top_cities],
        })


class MarketplaceFeatureResolveView(APIView):
    """Point d'entrée unique consommé par le frontend : « qu'est-ce que CET
    utilisateur peut voir et faire dans CE marketplace, maintenant ? ». Toute
    fonctionnalité ajoutée côté administration y apparaît automatiquement —
    aucune condition à coder à la main pour chaque nouveau bloc."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        marketplace_type = request.query_params.get("marketplace_type")
        valid_types = {choice[0] for choice in MarketplaceListing.MarketplaceType.choices}
        if marketplace_type not in valid_types:
            return Response({"detail": "Choisissez un espace marketplace valide."}, status=status.HTTP_400_BAD_REQUEST)
        resolved = resolve_features(request.user, marketplace_type)
        return Response(ResolvedFeatureSerializer(resolved, many=True).data)
