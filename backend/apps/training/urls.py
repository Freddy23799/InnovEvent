from rest_framework.routers import DefaultRouter

from .views import (
    BadgeViewSet,
    CertificateViewSet,
    EnrollmentViewSet,
    SettlementViewSet,
    TrainingFormulaViewSet,
    TrainingViewSet,
)

router = DefaultRouter()
router.register("enrollments", EnrollmentViewSet, basename="enrollment")
router.register("settlements", SettlementViewSet, basename="settlement")
router.register("certificates", CertificateViewSet, basename="certificate")
router.register("badges", BadgeViewSet, basename="badge")
router.register("formulas", TrainingFormulaViewSet, basename="training-formula")
router.register("", TrainingViewSet, basename="training")

urlpatterns = router.urls
