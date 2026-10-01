from rest_framework import serializers

from .models import AssistantConversation, AssistantMessage


class AssistantMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantMessage
        fields = ["id", "conversation", "role", "content", "recommendations", "created_at"]
        read_only_fields = fields


class AssistantConversationSerializer(serializers.ModelSerializer):
    messages = AssistantMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AssistantConversation
        fields = ["id", "user", "messages", "created_at"]
        read_only_fields = ["id", "user", "messages", "created_at"]


class AssistantPromptSerializer(serializers.Serializer):
    conversation = serializers.PrimaryKeyRelatedField(queryset=AssistantConversation.objects.all(), required=False)
    prompt = serializers.CharField(max_length=2000)
