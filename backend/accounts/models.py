import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


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
