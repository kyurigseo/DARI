from rest_framework import serializers

from .models import Persona, RehearsalFeedback, RehearsalMessage, RehearsalSession


class PersonaSerializer(serializers.ModelSerializer):
    persona_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = Persona
        fields = ["persona_id", "name", "culture_tag", "description"]


class FeedbackSerializer(serializers.ModelSerializer):
    feedback_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = RehearsalFeedback
        fields = [
            "feedback_id",
            "situation_label",
            "explanation",
            "original_text",
            "suggested_text",
            "translated_text",
            "translated_language",
            "is_saved_as_card",
        ]


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RehearsalMessage
        fields = ["id", "role", "content", "created_at"]


class SessionStartRequestSerializer(serializers.Serializer):
    persona_id = serializers.UUIDField()
    context = serializers.CharField(required=False, allow_blank=True, default="")


class SessionMessageRequestSerializer(serializers.Serializer):
    content = serializers.CharField(allow_blank=False)


class SaveCardRequestSerializer(serializers.Serializer):
    category = serializers.CharField(required=False, allow_blank=True, default="")


class SessionSummarySerializer(serializers.ModelSerializer):
    session_id = serializers.UUIDField(source="id", read_only=True)
    persona = PersonaSerializer(read_only=True)

    class Meta:
        model = RehearsalSession
        fields = ["session_id", "persona", "status", "started_at", "ended_at", "duration_sec"]
