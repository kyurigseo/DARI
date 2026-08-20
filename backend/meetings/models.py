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
    STATUS_CHOICES = [
        ('PENDING', '대기 중'),
        ('ACCEPTED', '수락'),
        ('REJECTED', '거절'),
    ]

    meeting = models.ForeignKey(MeetingSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_host = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    is_mic_on = models.BooleanField(default=True)
    is_camera_on = models.BooleanField(default=True)
    is_speaking = models.BooleanField(default=False)
    local_time_zone = models.CharField(max_length=50, default='UTC')

    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        unique_together = ('meeting', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.meeting.room_code} ({self.status})"

class MeetingTranscript(models.Model):
    meeting = models.ForeignKey(MeetingSession, on_delete=models.CASCADE, related_name='transcripts')
    speaker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    original_text = models.TextField()
    speaker_lang = models.CharField(max_length=10, default='auto')

    translations = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.speaker.username}] {self.original_text[:20]}"


class SpeechCard(models.Model):
    """
    [MVP 2 카드 파트 연동] 사용자가 사전에 리허설을 통해 생성한 발언카드
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='speech_cards')
    persona_name = models.CharField(max_length=100)
    situation = models.CharField(max_length=255)
    korean_script = models.TextField()
    translated_script = models.TextField()
    target_lang = models.CharField(max_length=10, default='EN')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.persona_name}] {self.situation}"


class MeetingChatMessage(models.Model):
    """
    [실시간 채팅 DB 저장 (S-001)]
    """
    meeting = models.ForeignKey(MeetingSession, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    is_speech_card = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender.username}] {self.message[:20]}"

class MeetingSummary(models.Model):
    """
    [AI 회의 요약 모델 (S-002)]
    회의 종료 후 LLM이 생성한 전체 핵심 요약문 저장
    """
    meeting = models.OneToOneField(
        MeetingSession,
        on_delete=models.CASCADE,
        related_name='summary'
    )
    content = models.TextField(help_text="AI가 생성한 회의 요약 본문")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.meeting.title}] AI 요약"


class MeetingMemo(models.Model):
    """
    [사용자별 직접 메모/요약 모델]
    회의별로 사용자가 직접 작성하고 관리하는 개인 메모
    """
    meeting = models.ForeignKey(
        MeetingSession,
        on_delete=models.CASCADE,
        related_name='memos'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='meeting_memos'
    )
    content = models.TextField(help_text="사용자 직접 메모 내용")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.user.username}] {self.meeting.title} 메모 ({self.content[:15]})"


class ActionItem(models.Model):
    """
    [Action Item 관리 모델 (S-003)]
    AI 추출 및 사용자가 편집 가능한 할 일, 담당자, 마감 기한, 완료 여부
    """
    meeting = models.ForeignKey(
        MeetingSession,
        on_delete=models.CASCADE,
        related_name='action_items'
    )
    task = models.CharField(max_length=255, help_text="할 일 내용")

    assignee = models.CharField(
        max_length=100,
        default='미지정',
        blank=True,
        help_text="담당자 이름 (기본값: 미지정)"
    )

    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="마감 기한 (미지정 시 None)"
    )

    is_completed = models.BooleanField(
        default=False,
        help_text="완료 여부 체크박스 상태"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        status = "완료" if self.is_completed else "진행중"
        return f"[{status}] {self.task} ({self.assignee} · {self.due_date or '기한 미지정'})"