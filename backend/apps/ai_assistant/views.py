from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AssistantConversation
from .serializers import AssistantConversationSerializer, AssistantPromptSerializer
from .services import ask_assistant


class AssistantConversationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AssistantConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AssistantConversation.objects.filter(user=self.request.user).prefetch_related("messages")


class AssistantAskView(APIView):
    """Point d'entrée conversationnel de l'assistant IA (section 12 du CDC)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AssistantPromptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = serializer.validated_data.get("conversation")
        if conversation is None or conversation.user_id != request.user.id:
            conversation = AssistantConversation.objects.create(user=request.user)

        assistant_message = ask_assistant(request.user, conversation, serializer.validated_data["prompt"])

        return Response({
            "conversation": conversation.id,
            "message": assistant_message.content,
            "recommendations": assistant_message.recommendations,
        })
