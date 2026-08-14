from django.contrib import admin

from .models import AvailabilitySlot, ParticipationRecord, ScheduledMeetingRequest


@admin.register(ParticipationRecord)
class ParticipationRecordAdmin(admin.ModelAdmin):
    list_display = ("participant", "meeting_title", "meeting_time_utc", "local_timezone", "speaking_duration_seconds")
    list_filter = ("local_timezone",)
    search_fields = ("participant__username", "meeting_title", "external_meeting_id")


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ("participant", "weekday", "half_hour_index", "status", "updated_at")
    list_filter = ("status", "weekday")
    search_fields = ("participant__username",)


@admin.register(ScheduledMeetingRequest)
class ScheduledMeetingRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "requested_by", "scheduled_start_time_utc", "room_code", "meetings_sync_status")
    list_filter = ("meetings_sync_status",)
    search_fields = ("title", "room_code", "requested_by__username")
