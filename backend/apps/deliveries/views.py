from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin, IsAdminClientOrOrganizer
from apps.audit.utils import log_action
from apps.bookings.models import Booking
from apps.marketplace.models import MarketplaceOrder
from apps.notifications.services import notify_delivery_assigned, notify_delivery_status_changed

from .models import Carrier, Delivery, DeliveryExpense, DeliveryProof, DeliveryReturn, DeliveryStatusHistory, DeliveryZone, Driver, PricingRule, Vehicle
from .pdf import build_delivery_note_pdf
from .reports import build_deliveries_csv, build_deliveries_report_pdf
from .serializers import (
    AdminCreateCarrierSerializer,
    CarrierSerializer,
    CreateDeliveryFromSourceSerializer,
    DeliveryAssignSerializer,
    UpdateLocationSerializer,
    DeliveryChangeStatusSerializer,
    DeliveryExpenseSerializer,
    DeliveryListSerializer,
    DeliveryProofSerializer,
    DeliveryReturnCreateSerializer,
    DeliveryReturnSerializer,
    DeliverySerializer,
    DeliveryTrackSerializer,
    DeliveryZoneSerializer,
    DriverSerializer,
    PricingRuleSerializer,
    VehicleSerializer,
)

User = get_user_model()


class DeliveryZoneViewSet(viewsets.ModelViewSet):
    """Zones tarifaires — lecture ouverte à tout compte authentifié (un
    transporteur doit pouvoir consulter les zones pour comprendre la
    tarification et créer/filtrer ses livraisons) ; écriture réservée à
    l'administration."""

    queryset = DeliveryZone.objects.all()
    serializer_class = DeliveryZoneSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdmin()]


class CarrierViewSet(viewsets.ModelViewSet):
    """Transporteurs — gestion complète par l'administration ; un compte
    transporteur (`Carrier.user` renseigné, rôle `partner`) ne voit et ne
    modifie que son propre enregistrement — même principe que `Driver.user`
    pour l'espace « Mes livraisons »."""

    queryset = Carrier.objects.select_related("service_zone", "user")
    serializer_class = CarrierSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["carrier_type", "status", "is_active"]
    search_fields = ["name", "company_name", "phone"]

    def get_permissions(self):
        if self.action in ("create", "destroy", "admin_create"):
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_admin_role:
            return qs
        return qs.filter(user=user)

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Retourne le transporteur lié au compte connecté (404 sinon) —
        utilisé par le frontend pour savoir si l'espace « Transporteur »
        doit être affiché."""
        carrier = Carrier.objects.filter(user=request.user).first()
        if not carrier:
            return Response({"detail": "Aucun profil transporteur pour ce compte."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CarrierSerializer(carrier).data)

    @action(detail=False, methods=["post"], url_path="admin-create")
    def admin_create(self, request):
        """Crée un compte transporteur — même pattern que
        `ProfessionalProfileViewSet.admin_create` (apps.marketplace) : compte
        `partner` existant sans transporteur, ou nouveau compte créé à la
        volée avec mot de passe généré."""
        serializer = AdminCreateCarrierSerializer(data=request.data)
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
        elif hasattr(owner, "carrier_profile"):
            raise ValidationError({"owner_user": "Ce compte a déjà un profil transporteur."})

        carrier = Carrier.objects.create(
            user=owner,
            name=data["name"],
            company_name=data.get("company_name", ""),
            carrier_type=data["carrier_type"],
            phone=data["phone"],
            whatsapp=data.get("whatsapp", ""),
            email=data.get("email", ""),
            address=data.get("address", ""),
            service_zone=data.get("service_zone"),
            transport_type=data.get("transport_type", ""),
            id_number=data.get("id_number", ""),
        )
        log_action(actor=request.user, action="carrier.account_created", metadata={"carrier": carrier.id, "owner": owner.id})

        response_data = CarrierSerializer(carrier).data
        response_data["owner_username"] = owner.username
        if generated_password:
            response_data["generated_password"] = generated_password
        return Response(response_data, status=status.HTTP_201_CREATED)


class VehicleViewSet(viewsets.ModelViewSet):
    """Véhicules — gestion complète par l'administration ; un compte
    transporteur ne voit et ne gère que les véhicules de sa propre flotte."""

    queryset = Vehicle.objects.select_related("carrier")
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["vehicle_type", "status", "carrier", "is_active"]
    search_fields = ["plate_number", "brand", "model"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_admin_role:
            return qs
        carrier_profile = getattr(user, "carrier_profile", None)
        if carrier_profile:
            return qs.filter(carrier=carrier_profile)
        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_admin_role:
            serializer.save()
            return
        carrier_profile = getattr(user, "carrier_profile", None)
        if not carrier_profile:
            raise PermissionDenied("Vous ne gérez pas de flotte de véhicules.")
        serializer.save(carrier=carrier_profile)

    def perform_update(self, serializer):
        user = self.request.user
        if user.is_admin_role:
            serializer.save()
            return
        # Empêche un transporteur de réaffecter un de ses véhicules à un
        # autre transporteur via une modification du champ `carrier`.
        serializer.save(carrier=getattr(user, "carrier_profile", None))


class DriverViewSet(viewsets.ModelViewSet):
    """Chauffeurs — gestion complète par l'administration ; un compte
    transporteur gère les chauffeurs de sa propre flotte, mais ne peut pas
    lier lui-même un compte utilisateur à un chauffeur (reste une action
    admin, cf. `admin-create` des transporteurs)."""

    queryset = Driver.objects.select_related("carrier", "current_vehicle", "user")
    serializer_class = DriverSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["status", "carrier", "is_active"]
    search_fields = ["full_name", "phone", "license_number"]

    def perform_destroy(self, instance):
        user = self.request.user
        carrier_profile = getattr(user, "carrier_profile", None)
        if not (user.is_admin_role or (carrier_profile and instance.carrier_id == carrier_profile.id)):
            # Un chauffeur consultant sa propre fiche (via get_queryset ci-
            # dessous) ne peut jamais la supprimer lui-même.
            raise PermissionDenied("Vous ne pouvez pas supprimer cette fiche chauffeur.")
        instance.delete()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_admin_role:
            return qs
        carrier_profile = getattr(user, "carrier_profile", None)
        if carrier_profile:
            return qs.filter(carrier=carrier_profile)
        driver_profile = getattr(user, "driver_profile", None)
        if driver_profile:
            # Un chauffeur ne voit que sa propre fiche — pour compléter ses
            # documents (CNI, permis, photo) — jamais celles des autres.
            return qs.filter(pk=driver_profile.id)
        return qs.none()

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Retourne la fiche chauffeur liée au compte connecté (404 sinon) —
        utilisée par l'espace « Mon profil chauffeur »."""
        driver = Driver.objects.filter(user=request.user).first()
        if not driver:
            return Response({"detail": "Aucune fiche chauffeur pour ce compte."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DriverSerializer(driver, context={"request": request}).data)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_admin_role:
            serializer.save()
            return
        carrier_profile = getattr(user, "carrier_profile", None)
        if not carrier_profile:
            raise PermissionDenied("Vous ne gérez pas d'équipe de chauffeurs.")
        serializer.save(carrier=carrier_profile, user=None)

    def perform_update(self, serializer):
        user = self.request.user
        if user.is_admin_role:
            serializer.save()
            return
        carrier_profile = getattr(user, "carrier_profile", None)
        if carrier_profile:
            # Un transporteur ne peut ni réaffecter un chauffeur à un autre
            # transporteur, ni lier/délier un compte utilisateur lui-même.
            serializer.save(carrier=carrier_profile, user=serializer.instance.user)
            return
        driver_profile = getattr(user, "driver_profile", None)
        if not driver_profile or driver_profile.id != serializer.instance.id:
            raise PermissionDenied("Vous ne pouvez modifier que votre propre profil chauffeur.")
        # Un chauffeur qui complète son propre profil ne touche jamais à son
        # affectation (transporteur, véhicule, statut, compte lié) — seulement
        # à ses informations personnelles et à ses documents.
        serializer.save(
            carrier=serializer.instance.carrier, current_vehicle=serializer.instance.current_vehicle,
            status=serializer.instance.status, user=serializer.instance.user, is_active=serializer.instance.is_active,
        )


class PricingRuleViewSet(viewsets.ModelViewSet):
    """Règles de tarification avancées (Phase 2) — gestion réservée à
    l'administration."""

    queryset = PricingRule.objects.select_related("zone")
    serializer_class = PricingRuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["zone", "vehicle_type", "priority", "is_active"]


class DeliveryExpenseViewSet(viewsets.ModelViewSet):
    """Dépenses transport (Phase 2) — administration en accès complet ; un
    transporteur ne voit et n'enregistre que les dépenses de sa propre
    flotte."""

    queryset = DeliveryExpense.objects.select_related("delivery", "carrier", "vehicle", "created_by")
    serializer_class = DeliveryExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["category", "carrier", "vehicle", "delivery"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_admin_role:
            return qs
        carrier_profile = getattr(user, "carrier_profile", None)
        if carrier_profile:
            return qs.filter(carrier=carrier_profile)
        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        extra = {"created_by": user}
        if not user.is_admin_role:
            carrier_profile = getattr(user, "carrier_profile", None)
            if not carrier_profile:
                raise PermissionDenied("Vous ne gérez pas de dépenses transport.")
            vehicle = serializer.validated_data.get("vehicle")
            delivery = serializer.validated_data.get("delivery")
            if vehicle and vehicle.carrier_id != carrier_profile.id:
                raise PermissionDenied("Ce véhicule n'appartient pas à votre flotte.")
            if delivery and delivery.carrier_id != carrier_profile.id:
                raise PermissionDenied("Cette livraison ne vous est pas affectée.")
            extra["carrier"] = carrier_profile
        expense = serializer.save(**extra)
        log_action(actor=user, action="delivery.expense.create", metadata={"expense": expense.id, "amount": str(expense.amount)})

    def perform_update(self, serializer):
        user = self.request.user
        if user.is_admin_role:
            serializer.save()
            return
        carrier_profile = getattr(user, "carrier_profile", None)
        vehicle = serializer.validated_data.get("vehicle")
        delivery = serializer.validated_data.get("delivery")
        if vehicle and vehicle.carrier_id != carrier_profile.id:
            raise PermissionDenied("Ce véhicule n'appartient pas à votre flotte.")
        if delivery and delivery.carrier_id != carrier_profile.id:
            raise PermissionDenied("Cette livraison ne vous est pas affectée.")
        serializer.save(carrier=carrier_profile)


class DeliveryViewSet(viewsets.ModelViewSet):
    """Livraisons — cœur du module.

    - Administration : accès complet.
    - Chauffeur (compte lié à un `Driver`) : ne voit que ses livraisons
      affectées, ne peut faire progresser leur statut que selon
      `Delivery.DRIVER_ALLOWED_TRANSITIONS`.
    - Client : ne voit que ses propres livraisons.
    - `track` (public, sans authentification) : suivi par code, aucune
      donnée sensible (section 6 du cahier des charges)."""

    queryset = Delivery.objects.select_related("client", "carrier", "driver", "vehicle", "zone").prefetch_related(
        "parcels", "status_history", "proof", "return_record"
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["status", "delivery_type", "priority", "carrier", "driver", "vehicle", "zone"]
    search_fields = ["reference", "tracking_code", "client_phone", "recipient_phone", "destination_address"]

    def get_serializer_class(self):
        if self.action == "list":
            return DeliveryListSerializer
        return DeliverySerializer

    def get_permissions(self):
        if self.action == "track":
            return [permissions.AllowAny()]
        if self.action in (
            "update", "partial_update", "destroy", "return_delivery",
            "create_from_booking", "create_from_order", "export",
        ):
            return [permissions.IsAuthenticated(), IsAdmin()]
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsAdminClientOrOrganizer()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if user.is_admin_role:
            return qs
        carrier_profile = getattr(user, "carrier_profile", None)
        if carrier_profile:
            qs = qs.filter(carrier=carrier_profile)
            if self.action == "list":
                # Espace transporteur simplifié : la liste ne montre que les
                # livraisons en cours — l'historique (livrées, annulées...)
                # reste accessible via une consultation directe (rapports,
                # dépenses) mais pas dans le fil de travail au quotidien.
                qs = qs.filter(status__in=Delivery.ACTIVE_STATUSES)
            return qs
        driver_profile = getattr(user, "driver_profile", None)
        if driver_profile:
            return qs.filter(driver=driver_profile)
        return qs.filter(client=user)

    def perform_create(self, serializer):
        user = self.request.user
        extra = {"created_by": user}
        if not user.is_admin_role:
            extra["client"] = user
        delivery = serializer.save(**extra)
        DeliveryStatusHistory.objects.create(
            delivery=delivery, actor=user, old_status="", new_status=delivery.status, comment="Création"
        )
        log_action(actor=user, action="delivery.create", metadata={"delivery": delivery.id})

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        delivery = self.get_object()
        user = request.user
        carrier_profile = getattr(user, "carrier_profile", None)
        if not user.is_admin_role and not (carrier_profile and delivery.carrier_id == carrier_profile.id):
            raise PermissionDenied("Vous ne pouvez affecter que vos propres livraisons.")

        serializer = DeliveryAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        carrier = serializer.validated_data.get("carrier")
        driver = serializer.validated_data.get("driver")
        vehicle = serializer.validated_data.get("vehicle")
        force = serializer.validated_data.get("force")

        if not user.is_admin_role:
            # Un transporteur ne peut pas réaffecter la livraison à un autre
            # transporteur, ni choisir un chauffeur/véhicule hors de sa flotte.
            carrier = carrier_profile
            if driver and driver.carrier_id != carrier_profile.id:
                raise PermissionDenied("Ce chauffeur n'appartient pas à votre flotte.")
            if vehicle and vehicle.carrier_id != carrier_profile.id:
                raise PermissionDenied("Ce véhicule n'appartient pas à votre flotte.")

        warnings = []
        if driver and driver.status != Driver.Status.AVAILABLE:
            warnings.append(f"Le chauffeur « {driver.full_name} » n'est pas marqué disponible.")
        if vehicle and vehicle.status != Vehicle.Status.AVAILABLE:
            warnings.append(f"Le véhicule « {vehicle.plate_number} » n'est pas marqué disponible.")
        if vehicle and vehicle.capacity_kg:
            total_weight = sum((p.weight_kg or 0) for p in delivery.parcels.all())
            if total_weight and total_weight > vehicle.capacity_kg:
                warnings.append(
                    f"Le poids total ({total_weight} kg) dépasse la capacité du véhicule ({vehicle.capacity_kg} kg)."
                )
        if driver:
            conflict = Delivery.objects.filter(driver=driver, status__in=Delivery.ACTIVE_STATUSES).exclude(pk=delivery.pk)
            if conflict.exists():
                warnings.append(f"« {driver.full_name} » a déjà {conflict.count()} livraison(s) active(s) en cours.")

        if warnings and not force:
            return Response({"warnings": warnings}, status=status.HTTP_409_CONFLICT)

        delivery.carrier = carrier
        delivery.driver = driver
        delivery.vehicle = vehicle
        old_status = delivery.status
        if old_status in (
            Delivery.Status.CREATED, Delivery.Status.PENDING, Delivery.Status.CONFIRMED,
            Delivery.Status.TO_PREPARE, Delivery.Status.READY,
        ) and (carrier or driver or vehicle):
            delivery.status = Delivery.Status.CARRIER_ASSIGNED
        delivery.save()
        if delivery.status != old_status:
            DeliveryStatusHistory.objects.create(
                delivery=delivery, actor=request.user, old_status=old_status, new_status=delivery.status,
                comment="Affectation transporteur/chauffeur/véhicule",
            )
        notify_delivery_assigned(delivery)
        log_action(
            actor=request.user, action="delivery.assign",
            metadata={
                "delivery": delivery.id, "carrier": carrier.id if carrier else None,
                "driver": driver.id if driver else None, "vehicle": vehicle.id if vehicle else None,
            },
        )
        return Response(DeliverySerializer(delivery, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        delivery = self.get_object()
        serializer = DeliveryChangeStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        comment = serializer.validated_data["comment"]
        user = request.user

        driver_profile = getattr(user, "driver_profile", None)
        carrier_profile = getattr(user, "carrier_profile", None)
        is_own_driver = bool(driver_profile and delivery.driver_id == driver_profile.id)
        is_own_carrier = bool(carrier_profile and delivery.carrier_id == carrier_profile.id)
        if not user.is_admin_role:
            if not (is_own_driver or is_own_carrier):
                raise PermissionDenied("Vous ne pouvez pas modifier cette livraison.")
            allowed_next = Delivery.DRIVER_ALLOWED_TRANSITIONS.get(delivery.status)
            if allowed_next != new_status:
                raise ValidationError(f"Transition non autorisée depuis « {delivery.get_status_display()} ».")

        old_status = delivery.status
        delivery.status = new_status
        update_fields = ["status", "updated_at"]
        if new_status == Delivery.Status.DELIVERED:
            # La position du client n'a plus de raison d'être partagée une
            # fois la livraison validée — on l'efface (jamais conservée
            # au-delà du besoin, voir Delivery.client_latitude).
            delivery.client_latitude = None
            delivery.client_longitude = None
            delivery.client_location_at = None
            update_fields += ["client_latitude", "client_longitude", "client_location_at"]
        delivery.save(update_fields=update_fields)
        DeliveryStatusHistory.objects.create(
            delivery=delivery, actor=user, old_status=old_status, new_status=new_status, comment=comment,
        )
        notify_delivery_status_changed(delivery)
        log_action(
            actor=user, action="delivery.status_change",
            metadata={"delivery": delivery.id, "old": old_status, "new": new_status},
        )
        return Response(DeliverySerializer(delivery, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="confirm-proof")
    def confirm_proof(self, request, pk=None):
        delivery = self.get_object()
        user = request.user
        driver_profile = getattr(user, "driver_profile", None)
        carrier_profile = getattr(user, "carrier_profile", None)
        is_own_driver = bool(driver_profile and delivery.driver_id == driver_profile.id)
        is_own_carrier = bool(carrier_profile and delivery.carrier_id == carrier_profile.id)
        if not user.is_admin_role and not (is_own_driver or is_own_carrier):
            raise PermissionDenied("Vous ne pouvez pas confirmer cette livraison.")

        DeliveryProof.objects.filter(delivery=delivery).delete()
        # `request.data` est un QueryDict/MultiValueDict en multipart (photo,
        # signature) — le spread `{**request.data, ...}` l'aplatit en dict
        # simple et corrompt les valeurs (fichiers comme chaînes). `.copy()`
        # préserve la sémantique QueryDict/MultiValueDict attendue par DRF.
        data = request.data.copy()
        data["delivery"] = delivery.id
        serializer = DeliveryProofSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        proof = serializer.save()
        # `delivery` vient de `get_object()` (déjà chargé) : sans ça, l'accès
        # à `delivery.proof` resterait figé sur « aucune preuve » pour le
        # reste de la requête (cache du descripteur OneToOne inversé).
        delivery.proof = proof

        old_status = delivery.status
        delivery.status = Delivery.Status.DELIVERED
        # Voir change_status : la position partagée par le client est
        # effacée dès que la livraison est validée.
        delivery.client_latitude = None
        delivery.client_longitude = None
        delivery.client_location_at = None
        delivery.save(update_fields=[
            "status", "updated_at", "client_latitude", "client_longitude", "client_location_at",
        ])
        DeliveryStatusHistory.objects.create(
            delivery=delivery, actor=user, old_status=old_status, new_status=delivery.status,
            comment="Preuve de livraison confirmée",
        )
        notify_delivery_status_changed(delivery)
        log_action(actor=user, action="delivery.proof_confirmed", metadata={"delivery": delivery.id})
        return Response(DeliverySerializer(delivery, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="update-location")
    def update_location(self, request, pk=None):
        """Position en direct du chauffeur pendant le transport — suivi
        cartographique léger (Leaflet/OpenStreetMap côté frontend, sans
        fournisseur payant). Seul le chauffeur affecté peut publier sa
        position ; jamais exposé sur le suivi public (section 6)."""
        delivery = self.get_object()
        user = request.user
        driver_profile = getattr(user, "driver_profile", None)
        if not user.is_admin_role and not (driver_profile and delivery.driver_id == driver_profile.id):
            raise PermissionDenied("Vous ne pouvez pas publier la position de cette livraison.")

        serializer = UpdateLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        delivery.last_latitude = serializer.validated_data["latitude"]
        delivery.last_longitude = serializer.validated_data["longitude"]
        delivery.last_location_at = timezone.now()
        delivery.save(update_fields=["last_latitude", "last_longitude", "last_location_at"])
        return Response(DeliverySerializer(delivery, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="update-client-location")
    def update_client_location(self, request, pk=None):
        """Position partagée par le CLIENT le temps du transport, pour
        faciliter la livraison. Seul le client destinataire peut la publier ;
        elle est effacée automatiquement dès validation (change_status /
        confirm_proof vers DELIVERED) — jamais conservée au-delà du besoin."""
        delivery = self.get_object()
        user = request.user
        if delivery.client_id != user.id:
            raise PermissionDenied("Vous ne pouvez pas publier la position de cette livraison.")

        serializer = UpdateLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        delivery.client_latitude = serializer.validated_data["latitude"]
        delivery.client_longitude = serializer.validated_data["longitude"]
        delivery.client_location_at = timezone.now()
        delivery.save(update_fields=["client_latitude", "client_longitude", "client_location_at"])
        return Response(DeliverySerializer(delivery, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        delivery = self.get_object()
        pdf_bytes = build_delivery_note_pdf(delivery)
        return FileResponse(
            BytesIO(pdf_bytes), as_attachment=True, filename=f"bon-livraison-{delivery.reference}.pdf",
            content_type="application/pdf",
        )

    @action(detail=False, methods=["get"])
    def track(self, request):
        code = (request.query_params.get("code") or "").strip().upper()
        if not code:
            return Response({"detail": "Code de suivi requis."}, status=status.HTTP_400_BAD_REQUEST)
        delivery = Delivery.objects.filter(tracking_code=code).first()
        if not delivery:
            return Response({"detail": "Aucune livraison trouvée pour ce code."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DeliveryTrackSerializer(delivery).data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Statistiques du tableau de bord transport (section 3) — admin
        (toutes les livraisons) ou transporteur (ses propres livraisons
        uniquement, protégé par `get_permissions`, action non listée donc
        `IsAuthenticated` par défaut : on vérifie explicitement ici)."""
        user = request.user
        carrier_profile = getattr(user, "carrier_profile", None)
        if user.is_admin_role:
            qs = Delivery.objects.all()
        elif carrier_profile:
            qs = Delivery.objects.filter(carrier=carrier_profile)
        else:
            raise PermissionDenied("Réservé à l'administration ou à un compte transporteur.")

        today = timezone.now().date()
        week_ago = timezone.now() - timedelta(days=7)

        by_day = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            by_day.append({"date": day.isoformat(), "count": qs.filter(created_at__date=day).count()})

        by_status = list(qs.values("status").annotate(count=Count("id")))

        paid_amount = sum(
            d.amount for d in qs.filter(status=Delivery.Status.DELIVERED, payment__isnull=False)
        )
        outstanding = sum(
            d.amount for d in qs.filter(payment__isnull=True).exclude(
                status__in=[Delivery.Status.CANCELLED, Delivery.Status.RETURNED]
            )
        )

        return Response({
            "total": qs.count(),
            "pending": qs.filter(status=Delivery.Status.PENDING).count(),
            "to_prepare": qs.filter(status=Delivery.Status.TO_PREPARE).count(),
            "in_progress": qs.filter(status__in=Delivery.ACTIVE_STATUSES).count(),
            "today": qs.filter(scheduled_date=today).count(),
            "scheduled": qs.filter(scheduled_date__gt=today).count(),
            "completed": qs.filter(status=Delivery.Status.DELIVERED).count(),
            "cancelled": qs.filter(status=Delivery.Status.CANCELLED).count(),
            "failed": qs.filter(status=Delivery.Status.FAILED).count(),
            "in_transit": qs.filter(status=Delivery.Status.IN_TRANSIT).count(),
            "revenue": paid_amount,
            "outstanding": outstanding,
            "active_carriers": (
                Carrier.objects.filter(status=Carrier.Status.AVAILABLE, is_active=True).count() if user.is_admin_role else 1
            ),
            "available_vehicles": Vehicle.objects.filter(
                status=Vehicle.Status.AVAILABLE, is_active=True, **({} if user.is_admin_role else {"carrier": carrier_profile})
            ).count(),
            "available_drivers": Driver.objects.filter(
                status=Driver.Status.AVAILABLE, is_active=True, **({} if user.is_admin_role else {"carrier": carrier_profile})
            ).count(),
            "by_day": by_day,
            "by_status": by_status,
        })

    @action(detail=True, methods=["post"], url_path="return")
    def return_delivery(self, request, pk=None):
        """Retour d'une livraison (Phase 2, section 17) — enregistre le motif
        et fait passer la livraison au statut « Retour en cours »."""
        delivery = self.get_object()
        serializer = DeliveryReturnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        DeliveryReturn.objects.filter(delivery=delivery).delete()
        return_record = DeliveryReturn.objects.create(delivery=delivery, initiated_by=request.user, **data)
        delivery.return_record = return_record

        old_status = delivery.status
        delivery.status = Delivery.Status.RETURNING
        delivery.save(update_fields=["status", "updated_at"])
        DeliveryStatusHistory.objects.create(
            delivery=delivery, actor=request.user, old_status=old_status, new_status=delivery.status,
            comment=f"Retour initié : {return_record.get_reason_display()}",
        )
        notify_delivery_status_changed(delivery)
        log_action(actor=request.user, action="delivery.return", metadata={"delivery": delivery.id, "reason": return_record.reason})
        return Response(DeliverySerializer(delivery, context={"request": request}).data)

    @action(detail=False, methods=["post"], url_path="create-from-booking")
    def create_from_booking(self, request):
        """Pont depuis une réservation existante (Phase 2, section 18) —
        pré-remplit une livraison sans dupliquer la validation de `Booking`."""
        booking = get_object_or_404(Booking, pk=request.data.get("booking"))
        if Delivery.objects.filter(related_booking=booking).exists():
            raise ValidationError("Une livraison existe déjà pour cette réservation.")
        serializer = CreateDeliveryFromSourceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        resource_label = {
            Booking.ResourceType.VENUE: booking.venue.name if booking.venue else "Salle",
            Booking.ResourceType.PROVIDER: booking.provider.name if booking.provider else "Prestataire",
            Booking.ResourceType.EQUIPMENT: booking.equipment.name if booking.equipment else "Matériel",
        }.get(booking.resource_type, "Ressource")

        delivery = Delivery.objects.create(
            client=booking.event.organizer,
            client_phone=getattr(booking.event.organizer, "phone", "") or "",
            recipient_name=booking.event.organizer.get_full_name() or booking.event.organizer.username,
            pickup_address=data["pickup_address"],
            destination_address=data["destination_address"] or "À préciser",
            delivery_type=Delivery.DeliveryType.LINKED_ORDER,
            description=f"Livraison pour la réservation « {resource_label} » — événement « {booking.event.title} »",
            scheduled_date=data["scheduled_date"],
            related_booking=booking,
            created_by=request.user,
        )
        DeliveryStatusHistory.objects.create(delivery=delivery, actor=request.user, old_status="", new_status=delivery.status, comment="Création depuis une réservation")
        log_action(actor=request.user, action="delivery.create_from_booking", metadata={"delivery": delivery.id, "booking": booking.id})
        return Response(DeliverySerializer(delivery, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="create-from-order")
    def create_from_order(self, request):
        """Pont depuis une commande marketplace existante (Phase 2, section 18)."""
        order = get_object_or_404(MarketplaceOrder, pk=request.data.get("order"))
        if Delivery.objects.filter(related_marketplace_order=order).exists():
            raise ValidationError("Une livraison existe déjà pour cette commande.")
        serializer = CreateDeliveryFromSourceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        delivery = Delivery.objects.create(
            client=order.buyer,
            recipient_name=order.buyer.get_full_name() or order.buyer.username,
            pickup_address=data["pickup_address"],
            destination_address=data["destination_address"] or "À préciser",
            delivery_type=Delivery.DeliveryType.LINKED_ORDER,
            description=f"Livraison pour la commande « {order.listing.title} »",
            scheduled_date=data["scheduled_date"],
            related_marketplace_order=order,
            created_by=request.user,
        )
        DeliveryStatusHistory.objects.create(delivery=delivery, actor=request.user, old_status="", new_status=delivery.status, comment="Création depuis une commande marketplace")
        log_action(actor=request.user, action="delivery.create_from_order", metadata={"delivery": delivery.id, "order": order.id})
        return Response(DeliverySerializer(delivery, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def export(self, request):
        """Export du rapport transport (Phase 2, section 22) — CSV ou PDF,
        avec les mêmes filtres que la liste (statut, dates)."""
        qs = self.filter_queryset(self.get_queryset()).select_related("carrier", "driver")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        # NB : le paramètre de requête « format » est réservé par DRF pour
        # la négociation de contenu (`URL_FORMAT_OVERRIDE`) — l'utiliser ici
        # provoquerait un 404 dès qu'aucun renderer DRF ne gère "csv"/"pdf".
        export_format = request.query_params.get("type", "csv")
        if export_format == "pdf":
            pdf_bytes = build_deliveries_report_pdf(qs, date_from=date_from, date_to=date_to)
            return FileResponse(
                BytesIO(pdf_bytes), as_attachment=True, filename="rapport-transport.pdf", content_type="application/pdf",
            )
        csv_content = build_deliveries_csv(qs)
        response = HttpResponse(csv_content, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=rapport-transport.csv"
        return response
