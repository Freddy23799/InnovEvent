from rest_framework.routers import DefaultRouter

from .views import EventExpenseViewSet, EventParticipantViewSet, EventTaskViewSet, EventViewSet

router = DefaultRouter()
router.register("tasks", EventTaskViewSet, basename="event-task")
router.register("participants", EventParticipantViewSet, basename="event-participant")
router.register("expenses", EventExpenseViewSet, basename="event-expense")
router.register("", EventViewSet, basename="event")

urlpatterns = router.urls
