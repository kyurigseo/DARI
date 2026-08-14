from rest_framework import serializers

from .models import AvailabilitySlot


class ParticipationIngestEntrySerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    local_timezone = serializers.CharField(max_length=64, default="UTC")
    local_region = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    speaking_duration_seconds = serializers.IntegerField(min_value=0, default=0)


class ParticipationIngestSerializer(serializers.Serializer):
    """
    meetings -> tracker 연동 스펙 (신규 제안):
    POST /api/v1/tracker/participation/ingest/
    Authorization: Internal <INTERNAL_SERVICE_TOKEN>
    body: {
      "external_meeting_id": "room_code",
      "meeting_title": "Q3 예산안 협상",
      "meeting_time_utc": "2026-08-15T09:00:00Z",
      "participants": [
        {"user_id": "<uuid>", "local_timezone": "Asia/Seoul", "local_region": "Seoul, KR",
         "speaking_duration_seconds": 420},
        ...
      ]
    }
    """

    external_meeting_id = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    meeting_title = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    meeting_time_utc = serializers.DateTimeField()
    participants = ParticipationIngestEntrySerializer(many=True)


class AvailabilitySlotSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="participant.username", read_only=True)
    user_id = serializers.UUIDField(source="participant_id", read_only=True)

    class Meta:
        model = AvailabilitySlot
        fields = ["user_id", "username", "weekday", "half_hour_index", "status", "updated_at"]


class AvailabilitySlotUpsertSerializer(serializers.Serializer):
    weekday = serializers.IntegerField(min_value=0, max_value=6)
    half_hour_index = serializers.IntegerField(min_value=0, max_value=47)
    status = serializers.ChoiceField(choices=AvailabilitySlot.STATUS_CHOICES)


class ParticipantIdsQuerySerializer(serializers.Serializer):
    participant_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class MeetingConfirmSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    weekday = serializers.IntegerField(min_value=0, max_value=6)
    half_hour_index = serializers.IntegerField(min_value=0, max_value=47)
    participant_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=True, default=list)
