from rest_framework.routers import DefaultRouter

from .views import TalentPortfolioItemViewSet, TalentProfileViewSet

router = DefaultRouter()
router.register("portfolio", TalentPortfolioItemViewSet, basename="talent-portfolio")
router.register("", TalentProfileViewSet, basename="talent-profile")

urlpatterns = router.urls
