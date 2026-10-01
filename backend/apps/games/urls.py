from rest_framework.routers import DefaultRouter

from .views import QuizAttemptViewSet, QuizQuestionViewSet, QuizViewSet

router = DefaultRouter()
router.register("questions", QuizQuestionViewSet, basename="quiz-question")
router.register("attempts", QuizAttemptViewSet, basename="quiz-attempt")
router.register("", QuizViewSet, basename="quiz")

urlpatterns = router.urls
