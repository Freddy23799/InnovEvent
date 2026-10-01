from rest_framework.routers import DefaultRouter

from .views import (
    CarrierViewSet,
    DeliveryExpenseViewSet,
    DeliveryViewSet,
    DeliveryZoneViewSet,
    DriverViewSet,
    PricingRuleViewSet,
    VehicleViewSet,
)

router = DefaultRouter()
router.register("zones", DeliveryZoneViewSet, basename="delivery-zones")
router.register("carriers", CarrierViewSet, basename="carriers")
router.register("drivers", DriverViewSet, basename="drivers")
router.register("vehicles", VehicleViewSet, basename="vehicles")
router.register("pricing-rules", PricingRuleViewSet, basename="pricing-rules")
router.register("expenses", DeliveryExpenseViewSet, basename="delivery-expenses")
router.register("", DeliveryViewSet, basename="deliveries")

urlpatterns = router.urls
