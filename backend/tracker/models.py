import uuid

from django.conf import settings
from django.db import models


class ParticipationRecord(models.Model):
    """
    참가자 1명이 회의 1건에 참여한 기록. meeting_time_utc는 항상 UTC로 저장하고,
    "새벽/주간/저녁" 분류는 조회 시점에 local_timezone으로 변환해서 계산한다
    (분류 기준이 나중에 바뀌어도 원본 데이터를 다시 저장할 필요가 없도록).

    meetings 앱이 회의 종료 후 POST /api/v1/tracker/participation/ingest/ 로
    참가자 지역 + 발화 시간 데이터를 넣어줄 때 생성된다.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="participation_records"
    )
    external_meeting_id = models.CharField(
        max_length=100, blank=True, help_text="meetings.MeetingSession.room_code (있으면)"
    )
    meeting_title = models.CharField(max_length=255, blank=True)
    meeting_time_utc = models.DateTimeField(help_text="회의 시각 (UTC)")
    local_timezone = models.CharField(
        max_length=64, default="UTC", help_text="참가자 로컬 IANA 타임존 (예: Asia/Seoul)"
    )
    local_region = models.CharField(
        max_length=100, blank=True, help_text="참가자 지역 표시명(meetings가 전달). 없으면 타임존으로 대체 표시"
    )
    speaking_duration_seconds = models.PositiveIntegerField(
        default=0, help_text="회의 중 발화 시간(초). meetings가 회의 종료 후 전달"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-meeting_time_utc"]
        indexes = [models.Index(fields=["participant", "-meeting_time_utc"])]

    def __str__(self):
        return f"{self.participant.username} @ {self.meeting_time_utc.isoformat()}"


class AvailabilitySlot(models.Model):
    """
    "모두의 시간 찾기" 히트맵 한 칸. weekday/half_hour_index는 UTC 기준 주간 반복 좌표라서
    참가자마다 다른 로컬 타임존이어도 전원이 같은 좌표계(UTC) 위에서 비교된다.
    실제 로컬 시각으로 보여주는 건 프론트(혹은 응답 직렬화 시 부가 정보)의 몫이다.

    본인 행만 수정 가능해야 하므로, 쓰기는 항상 request.user를 participant로 강제하는
    전용 엔드포인트(HeatmapMeUpdateView)를 통해서만 이루어진다 — 모델 자체는 제약을 걸지 않는다.
    """

    COMFORTABLE = "COMFORTABLE"
    NEUTRAL = "NEUTRAL"
    UNCOMFORTABLE = "UNCOMFORTABLE"
    STATUS_CHOICES = [
        (COMFORTABLE, "편한 시간"),
        (NEUTRAL, "보통"),
        (UNCOMFORTABLE, "불편한 시간"),
    ]

    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="availability_slots"
    )
    weekday = models.PositiveSmallIntegerField(help_text="0=월요일 ... 6=일요일 (UTC 기준)")
    half_hour_index = models.PositiveSmallIntegerField(
        help_text="0~47, 하루 중 30분 단위 슬롯 인덱스 (UTC 00:00부터)"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=NEUTRAL)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["participant", "weekday", "half_hour_index"], name="tracker_unique_participant_slot"
            )
        ]
        indexes = [models.Index(fields=["weekday", "half_hour_index"])]

    def __str__(self):
        return f"{self.participant.username} {self.weekday}/{self.half_hour_index} {self.status}"


class ScheduledMeetingRequest(models.Model):
    """
    "이 시간으로 일정 확정하기" 클릭 기록.

    meetings.MeetingSession에는 아직 예정 시각(scheduled_start_time) 필드가 없어서
    (CreateMeetingView가 title/room_code만 받음), 확정된 시각·참가자 정보는 우선
    tracker 쪽에 보관하고 room_code로 meetings의 실제 회의방과 연결한다.
    meetings_sync_status로 실제 방 생성/초대가 성공했는지 추적한다.
    """

    SYNC_PENDING = "PENDING"
    SYNC_SYNCED = "SYNCED"
    SYNC_FAILED = "FAILED"
    SYNC_STATUS_CHOICES = [
        (SYNC_PENDING, "대기"),
        (SYNC_SYNCED, "동기화 완료"),
        (SYNC_FAILED, "동기화 실패"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scheduled_meeting_requests"
    )
    title = models.CharField(max_length=255)
    room_code = models.CharField(max_length=50, blank=True, help_text="meetings.MeetingSession.room_code")
    scheduled_start_time_utc = models.DateTimeField()
    participant_ids = models.JSONField(default=list, help_text="확정 시점 참가자 user id 목록(호스트 포함)")
    meetings_sync_status = models.CharField(
        max_length=20, choices=SYNC_STATUS_CHOICES, default=SYNC_PENDING
    )
    meetings_sync_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.meetings_sync_status}] {self.title} ({self.scheduled_start_time_utc.isoformat()})"
