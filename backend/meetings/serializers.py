# 회의 API 시리얼라이저

from rest_framework import serializers
from .models import MeetingSession, MeetingParticipant

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