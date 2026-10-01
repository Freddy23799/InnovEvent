from rest_framework.routers import DefaultRouter

from .views import EquipmentReviewViewSet, ProfessionalReviewViewSet, ProviderReviewViewSet, VenueReviewViewSet

router = DefaultRouter()
router.register("venues", VenueReviewViewSet, basename="venue-review")
router.register("providers", ProviderReviewViewSet, basename="provider-review")
router.register("equipment", EquipmentReviewViewSet, basename="equipment-review")
router.register("professionals", ProfessionalReviewViewSet, basename="professional-review")

urlpatterns = router.urls
