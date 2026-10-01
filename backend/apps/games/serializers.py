from rest_framework import serializers

from .models import Quiz, QuizAttempt, QuizQuestion


class QuizSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(read_only=True)
    event_title = serializers.CharField(source="event.title", read_only=True, default=None)
    best_score = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id", "title", "category", "description", "event", "event_title",
            "is_active", "question_count", "best_score", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_best_score(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        best = obj.attempts.filter(participant=request.user).order_by("-score").first()
        return {"score": best.score, "total_questions": best.total_questions, "percent": best.percent} if best else None


class QuizQuestionAdminSerializer(serializers.ModelSerializer):
    """Vue complète (avec la bonne réponse) réservée à la gestion admin."""

    class Meta:
        model = QuizQuestion
        fields = ["id", "quiz", "text", "choices", "correct_index", "order"]
        read_only_fields = ["id"]


class QuizQuestionPlaySerializer(serializers.ModelSerializer):
    """Vue joueur : jamais la bonne réponse, pour ne pas la révéler côté client."""

    class Meta:
        model = QuizQuestion
        fields = ["id", "text", "choices", "order"]


class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = QuizAttempt
        fields = ["id", "quiz", "quiz_title", "score", "total_questions", "percent", "completed_at"]
        read_only_fields = fields


class QuizSubmitSerializer(serializers.Serializer):
    answers = serializers.DictField(
        child=serializers.IntegerField(),
        help_text="Réponses soumises : {question_id (str): chosen_index}",
    )
