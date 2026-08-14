import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    COUNTRY_CHOICES = [
        ("KR", "대한민국"),
        ("US", "미국"),
        ("DE", "독일"),
        ("JP", "일본"),
        ("CN", "중국"),
        ("OTHER", "기타"),
    ]

    ROLE_CHOICES = [
        ("STUDENT", "학생"),
        ("STAFF", "사원·직원"),
        ("MANAGER", "팀장·매니저"),
        ("EXECUTIVE", "임원·C-level"),
        ("FREELANCER", "프리랜서"),
        ("FOUNDER", "창업가·대표"),
        ("OTHER", "기타"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    country = models.CharField(max_length=10, choices=COUNTRY_CHOICES)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return self.username

class UserProfile(models.Model):
    """
    [마이페이지 프로필 & 설정]
    기존 User 모델과 1:1로 매핑되어 마이페이지에 필요한 추가 정보를 관리
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    profile_image = models.ImageField(
        upload_to='profile_images/',
        null=True,
        blank=True,
        help_text="프로필 사진"
    )
    position_team = models.CharField(
        max_length=100,
        default="PM · Acme팀",
        blank=True,
        help_text="직함 및 소속 팀"
    )
    completed_rehearsals_count = models.PositiveIntegerField(
        default=0,
        help_text="완료한 리허설 총 횟수"
    )
    notification_enabled = models.BooleanField(
        default=True,
        help_text="알림 받기 On/Off"
    )
    preferred_language = models.CharField(
        max_length=20,
        default="한국어",
        help_text="기본 번역 선호 언어"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.user.username}] {self.position_team} 프로필"

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()