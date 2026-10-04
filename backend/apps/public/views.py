import mimetypes
from datetime import datetime, time
from io import BytesIO

from django.db import transaction
from django.core.files.storage import default_storage
from django.http import FileResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.views.decorators.http import require_GET

from apps.accounts.permissions import IsAdminOrPublicReadOnly
from apps.bookings.serializers import BookingSerializer
from apps.events.models import Event
from apps.notifications.services import notify_booking_created

from .models import LandingMedia, PackItem
from .pdf import build_pack_preview_pdf
from .serializers import LandingMediaSerializer, PackItemSerializer


@require_GET
def public_landing_media_file(request, path):
    """Sert uniquement les photos publiques de la vitrine.

    En Docker, Nginx sert normalement ``/media/``. Certains hébergements
    cPanel/Passenger ne permettent pas de déclarer cet alias Apache : cette
    route rend alors la photothèque publique disponible sans rendre publics
    les documents sensibles téléversés ailleurs dans l'application (CNI,
    permis, pièces jointes, etc.).
    """
    storage_name = f"landing/{path}"
    if not LandingMedia.objects.filter(image=storage_name, is_active=True).exists():
        from django.http import Http404

        raise Http404("Média public introuvable.")

    try:
        file_handle = default_storage.open(storage_name, "rb")
    except (FileNotFoundError, OSError):
        from django.http import Http404

        raise Http404("Fichier média introuvable.")

    content_type = mimetypes.guess_type(storage_name)[0] or "application/octet-stream"
    return FileResponse(file_handle, content_type=content_type)


def _parse_selections(raw_selections):
    """Normalise la liste `[{pack_item_id, quantity}]` envoyée par le
    frontend — jamais fait confiance aveuglément, mais tolérant aux valeurs
    manquantes/mal formées plutôt que de faire échouer toute la requête."""
    qty_by_id = {}
    ids = []
    for entry in raw_selections or []:
        try:
            item_id = int(entry.get("pack_item_id"))
        except (TypeError, ValueError, AttributeError):
            continue
        ids.append(item_id)
        try:
            qty_by_id[item_id] = max(1, int(entry.get("quantity") or 1))
        except (TypeError, ValueError):
            qty_by_id[item_id] = 1
    return ids, qty_by_id


class LandingMediaViewSet(ModelViewSet):
    """Photothèque de la page d'accueil : lecture publique (page marketing,
    filtrable par `?category=`), gestion (ajout/modification/suppression)
    réservée à l'administration (section « Gestion du site » du back-office)."""

    serializer_class = LandingMediaSerializer
    permission_classes = [IsAdminOrPublicReadOnly]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["category", "is_active"]
    ordering_fields = ["order", "created_at"]

    def get_queryset(self):
        qs = LandingMedia.objects.all()
        if not (self.request.user and self.request.user.is_authenticated and self.request.user.is_admin_role):
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        if self.action == "quote_preview":
            # Aperçu tarifaire non contractuel — volontairement ouvert sans
            # connexion (page publique), contrairement à la vraie demande de
            # devis (quote_request) qui exige un compte.
            return [permissions.AllowAny()]
        if self.action == "quote_request":
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, methods=["post"], url_path="quote-preview")
    def quote_preview(self, request, pk=None):
        pack = self.get_object()
        if pack.category != LandingMedia.Category.PACK:
            return Response({"detail": "Cet élément n'est pas un pack."}, status=400)

        ids, qty_by_id = _parse_selections(request.data.get("selections"))
        items = PackItem.objects.filter(pack=pack, id__in=ids).select_related("venue", "provider", "equipment")
        lines = []
        total = 0
        for item in items:
            resource = item.resource
            if not resource:
                continue
            quantity = qty_by_id.get(item.id, item.default_quantity)
            price = getattr(resource, "price_per_unit", None)
            if price is None:
                price = getattr(resource, "price_per_day", None)
            subtotal = float(price) * quantity if price else None
            if subtotal is not None:
                total += subtotal
            lines.append({"name": resource.name, "quantity": quantity, "subtotal": subtotal})

        pdf_bytes = build_pack_preview_pdf(pack, lines, total)
        return FileResponse(BytesIO(pdf_bytes), content_type="application/pdf", filename=f"apercu-pack-{pack.pk}.pdf")

    @action(detail=True, methods=["post"], url_path="quote-request")
    def quote_request(self, request, pk=None):
        """Demande de devis groupée pour tout le pack : crée l'événement du
        client et UNE réservation par élément sélectionné, en une seule
        soumission — plutôt que de le laisser réserver chaque élément
        séparément après coup. Réutilise BookingSerializer (détection de
        conflits incluse) pour chaque ligne."""
        pack = self.get_object()
        if pack.category != LandingMedia.Category.PACK:
            return Response({"detail": "Cet élément n'est pas un pack."}, status=400)

        event_date = parse_date(request.data.get("event_date") or "")
        if not event_date:
            return Response({"detail": "La date de l'événement est requise."}, status=400)

        event_title = (request.data.get("event_title") or "").strip() or f"{pack.label} — {event_date.strftime('%d/%m/%Y')}"
        notes = (request.data.get("notes") or "").strip()

        ids, qty_by_id = _parse_selections(request.data.get("selections"))
        items = list(PackItem.objects.filter(pack=pack, id__in=ids).select_related("venue", "provider", "equipment"))
        if not items:
            return Response({"detail": "Sélectionnez au moins un élément du pack."}, status=400)

        start_dt = timezone.make_aware(datetime.combine(event_date, time(8, 0)))
        end_dt = timezone.make_aware(datetime.combine(event_date, time(23, 0)))

        with transaction.atomic():
            event = Event.objects.create(
                title=event_title, organizer=request.user, start_date=start_dt, end_date=end_dt,
                description=f"Créé automatiquement depuis la demande de devis du pack « {pack.label} ».",
            )
            bookings = []
            for item in items:
                resource = item.resource
                if not resource:
                    continue
                quantity = qty_by_id.get(item.id, item.default_quantity)
                payload = {
                    "event": event.id, "resource_type": item.resource_type,
                    "quantity": quantity if item.resource_type == "equipment" else 1,
                    "start_datetime": start_dt, "end_datetime": end_dt, "notes": notes,
                    item.resource_type: resource.id,
                }
                serializer = BookingSerializer(data=payload)
                serializer.is_valid(raise_exception=True)
                bookings.append(serializer.save(created_by=request.user))
            if not bookings:
                raise ValidationError("Aucun élément valide sélectionné.")

        for booking in bookings:
            notify_booking_created(booking)

        return Response(
            {"event": event.id, "bookings": BookingSerializer(bookings, many=True).data},
            status=201,
        )


class PackItemViewSet(ModelViewSet):
    """Composants d'un pack (« Découvrir le pack ») : lecture publique filtrable
    par `?pack=`, gestion réservée à l'administration."""

    serializer_class = PackItemSerializer
    permission_classes = [IsAdminOrPublicReadOnly]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["pack", "resource_type"]
    ordering_fields = ["order"]
    queryset = PackItem.objects.select_related("venue", "provider", "equipment")
