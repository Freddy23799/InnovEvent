from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AssistantAskView, AssistantConversationViewSet

router = DefaultRouter()
router.register("conversations", AssistantConversationViewSet, basename="assistant-conversation")

urlpatterns = [
    path("ask/", AssistantAskView.as_view(), name="assistant-ask"),
] + router.urls
