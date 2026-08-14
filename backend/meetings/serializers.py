# 회의 API 시리얼라이저

from rest_framework import serializers
from .models import MeetingSession, MeetingParticipant, SpeechCard, MeetingChatMessage

class SpeechCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpeechCard
        fields = ['id', 'persona_name', 'situation', 'korean_script', 'translated_script', 'target_lang', 'created_at']


class MeetingChatMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = MeetingChatMessage
        fields = ['id', 'meeting', 'sender', 'sender_username', 'message', 'is_speech_card', 'created_at']


class ParticipantSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = MeetingParticipant
        fields = ['id', 'user', 'username', 'is_host', 'is_mic_on', 'is_camera_on', 'is_speaking', 'local_time_zone', 'is_active']


class MeetingSessionSerializer(serializers.ModelSerializer):
    participants = ParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = MeetingSession
        fields = ['id', 'room_code', 'title', 'host', 'status', 'created_at', 'participants']