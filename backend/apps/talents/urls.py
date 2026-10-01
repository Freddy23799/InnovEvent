from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import TalentMissionContactView, TalentMissionListView, TalentMissionManageViewSet, TalentPortfolioItemViewSet, TalentProfileViewSet

router = DefaultRouter()
router.register("portfolio", TalentPortfolioItemViewSet, basename="talent-portfolio")
router.register("", TalentProfileViewSet, basename="talent-profile")

urlpatterns = [path("missions/manage/", TalentMissionManageViewSet.as_view({"get": "list", "post": "create"}), name="talent-missions-manage"), path("missions/manage/<int:pk>/", TalentMissionManageViewSet.as_view({"patch": "partial_update", "delete": "destroy"}), name="talent-mission-manage-detail"), path("missions/", TalentMissionListView.as_view(), name="talent-missions"), path("missions/<int:mission_id>/contact/", TalentMissionContactView.as_view(), name="talent-mission-contact")] + router.urls
