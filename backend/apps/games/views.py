from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin, IsAdminOrReadOnly
from apps.audit.utils import log_action

from .models import Quiz, QuizAttempt, QuizQuestion
from .serializers import (
    QuizAttemptSerializer,
    QuizQuestionAdminSerializer,
    QuizQuestionPlaySerializer,
    QuizSerializer,
    QuizSubmitSerializer,
)


class QuizViewSet(viewsets.ModelViewSet):
    """Jeux-questionnaires : catalogue consultable par tout utilisateur authentifié,
    gestion (création/édition des quiz) réservée à l'administration."""

    serializer_class = QuizSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["category", "is_active", "event"]

    def get_queryset(self):
        qs = Quiz.objects.select_related("event").prefetch_related("questions")
        if self.request.user.is_authenticated and self.request.user.is_admin_role:
            return qs
        return qs.filter(is_active=True)

    @action(detail=True, methods=["get"], url_path="questions")
    def questions(self, request, pk=None):
        quiz = self.get_object()
        questions = quiz.questions.all()
        return Response(QuizQuestionPlaySerializer(questions, many=True).data)

    @action(detail=True, methods=["post"], url_path="submit", permission_classes=[permissions.IsAuthenticated])
    def submit(self, request, pk=None):
        quiz = self.get_object()
        serializer = QuizSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submitted = serializer.validated_data["answers"]

        questions = list(quiz.questions.all())
        score = 0
        review = []
        for question in questions:
            chosen = submitted.get(str(question.id))
            is_correct = chosen == question.correct_index
            if is_correct:
                score += 1
            review.append({
                "question_id": question.id,
                "text": question.text,
                "choices": question.choices,
                "chosen_index": chosen,
                "correct_index": question.correct_index,
                "is_correct": is_correct,
            })

        attempt = QuizAttempt.objects.create(
            quiz=quiz, participant=request.user,
            score=score, total_questions=len(questions), answers=submitted,
        )
        log_action(
            actor=request.user, action="quiz.attempt",
            metadata={"quiz": quiz.title, "score": score, "total": len(questions)},
        )

        return Response({
            "attempt": QuizAttemptSerializer(attempt).data,
            "review": review,
        })


class QuizQuestionViewSet(viewsets.ModelViewSet):
    """Gestion des questions d'un quiz — réservée à l'administration (la bonne
    réponse ne doit jamais être exposée hors de cette vue de gestion)."""

    serializer_class = QuizQuestionAdminSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["quiz"]
    queryset = QuizQuestion.objects.select_related("quiz")


class QuizAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """Historique des tentatives : chacun voit les siennes, l'administration voit tout."""

    serializer_class = QuizAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["quiz"]

    def get_queryset(self):
        qs = QuizAttempt.objects.select_related("quiz")
        if self.request.user.is_admin_role:
            return qs
        return qs.filter(participant=self.request.user)
