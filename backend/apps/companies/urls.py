from rest_framework.routers import DefaultRouter

from .views import CompanyDocumentViewSet, CompanyProfileViewSet

router = DefaultRouter()
router.register("documents", CompanyDocumentViewSet, basename="company-document")
router.register("", CompanyProfileViewSet, basename="company-profile")

urlpatterns = router.urls
