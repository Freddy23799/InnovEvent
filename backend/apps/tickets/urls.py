from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MyTicketsViewSet, TicketPurchaseView, TicketScanView, TicketTypeViewSet

router = DefaultRouter()
router.register("types", TicketTypeViewSet, basename="ticket-type")
router.register("my", MyTicketsViewSet, basename="my-ticket")

urlpatterns = [
    path("purchase/", TicketPurchaseView.as_view(), name="ticket-purchase"),
    path("scan/", TicketScanView.as_view(), name="ticket-scan"),
] + router.urls
