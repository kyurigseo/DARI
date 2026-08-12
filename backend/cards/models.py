import uuid

from django.conf import settings
from django.db import models


class Card(models.Model):
    """
    발언 카드. CLAUDE.md 카드 UI 요구사항(상대 태그 + 상황 라벨 + 한국어/원어 두 줄)만
    반영하고, 실제 화면에서 쓰이지 않는 category 등은 넣지 않았다.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cards")
    partner_tag = models.CharField(max_length=50, help_text="상대 태그 (예: 독일 팀장님)")
    situation_label = models.CharField(max_length=100, help_text="상황 라벨")
    text_ko = models.TextField(help_text="원문 (한국어)")
    text_translated = models.TextField(help_text="번역문 (원어)")
    language_code = models.CharField(max_length=10, help_text="번역문 언어 코드 (예: de, ja, zh, en)")
    explanation = models.TextField(blank=True, help_text="개선 방향 코멘트 (rehearsal에서 전달, optional)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.partner_tag} - {self.situation_label}"
