# 회의 세션 및 참가자 모델

import uuid
from django.db import models
from django.conf import settings

class MeetingSession(models.Model):
    STATUS_CHOICES = (
        ('WAITING', '대기 중'),
        ('ONGOING', '진행 중'),
        ('ENDED', '종료됨'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_code = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=255)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_meetings')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='WAITING')
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.room_code}] {self.title}"


class MeetingParticipant(models.Model):
    meeting = models.ForeignKey(MeetingSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_host = models.BooleanField(default=False)


    is_mic_on = models.BooleanField(default=True)
    is_camera_on = models.BooleanField(default=True)
    is_speaking = models.BooleanField(default=False)
    local_time_zone = models.CharField(max_length=50, default='UTC')

    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True) # 현재 접속 여부

    class Meta:
        unique_together = ('meeting', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.meeting.room_code}"