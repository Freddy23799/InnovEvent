from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ProviderScanView, ProviderViewSet

router = DefaultRouter()
router.register("", ProviderViewSet, basename="provider")

urlpatterns = [
    path("scan/", ProviderScanView.as_view(), name="provider-scan"),
] + router.urls
