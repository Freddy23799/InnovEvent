from rest_framework.routers import DefaultRouter

from .views import LandingMediaViewSet, PackItemViewSet

router = DefaultRouter()
router.register("landing-media", LandingMediaViewSet, basename="landing-media")
router.register("pack-items", PackItemViewSet, basename="pack-items")

urlpatterns = router.urls
