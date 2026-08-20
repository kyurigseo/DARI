import uuid

from django.conf import settings
from django.db import models


class Persona(models.Model):
    """
    리허설 상대역. culture_tag는 고정 enum이 아니라 자유 문자열로 두고 실제 4종은
    데이터 마이그레이션(0002_seed_personas)으로 시드한다. 새 페르소나 추가는 코드/스키마
    변경 없이 DB row 추가만으로 가능하도록 하기 위함 ("이후 추가 가능하도록" 요구사항).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    culture_tag = models.CharField(max_length=30)
    language_code = models.CharField(
        max_length=10, help_text="피드백 번역에 쓰는 ISO 639-1 코드 (de/ja/zh/en 등)"
    )
    description = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class RehearsalSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "진행 중"
        ENDED = "ENDED", "종료"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rehearsal_sessions"
    )
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="sessions")
    context = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_sec = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]


class RehearsalMessage(models.Model):
    """
    세션의 대화 히스토리(AI 질문/사용자 응답 turn)를 모두 저장한다.
    - 세션 종료 시 feedback_list를 만들려면 turn 순서가 필요하고,
    - 홈 화면 "AI 리허설 이어하기"가 마지막 메시지 미리보기를 보여줘야 하므로
    저장하지 않으면 두 기능을 만들 수 없어 영속화하기로 결정했다.
    """

    class Role(models.TextChoices):
        AI = "AI", "AI"
        USER = "USER", "사용자"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(RehearsalSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class RehearsalFeedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(RehearsalSession, on_delete=models.CASCADE, related_name="feedbacks")
    user_message = models.ForeignKey(
        RehearsalMessage, on_delete=models.CASCADE, related_name="feedback"
    )
    situation_label = models.CharField(max_length=100)
    explanation = models.TextField(help_text="개선 방향 코멘트")
    original_text = models.TextField(help_text="사용자가 실제로 입력한 응답 원문")
    suggested_text = models.TextField(help_text="AI가 추천하는 한국어 문구")
    translated_text = models.TextField(help_text="suggested_text의 상대 언어 번역")
    translated_language = models.CharField(max_length=10)
    category = models.CharField(max_length=30, blank=True)
    is_saved_as_card = models.BooleanField(default=False)
    card_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
