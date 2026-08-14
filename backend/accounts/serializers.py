from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User,  UserProfile
from django.contrib.auth import get_user_model
from django.db.models import Q
from meetings.models import MeetingSession, SpeechCard

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "country", "role"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "country", "role", "date_joined"]
        read_only_fields = fields

User = get_user_model()

class MyPageResponseSerializer(serializers.ModelSerializer):
    """
    [마이페이지 종합 조회 시리얼라이저]
    - 기본 프로필 정보
    - 활동 통계 (발언카드, 리허설, 참여 회의 수)
    - 환경 설정 (알림, 번역 언어)
    """
    name = serializers.CharField(source='username', read_only=True)
    position_team = serializers.CharField(source='profile.position_team', read_only=True)
    profile_image = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'name',
            'email',
            'position_team',
            'profile_image',
            'stats',
            'settings',
        ]

    def get_profile_image(self, obj):
        if hasattr(obj, 'profile') and obj.profile.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile.profile_image.url)
            return obj.profile.profile_image.url
        return None

    def get_stats(self, obj):
        saved_cards_count = SpeechCard.objects.filter(user=obj).count() if hasattr(SpeechCard, 'user') else SpeechCard.objects.count()
        completed_rehearsals = getattr(obj.profile, 'completed_rehearsals_count', 0) if hasattr(obj, 'profile') else 0
        joined_meetings_count = MeetingSession.objects.filter(
            Q(host=obj) | Q(participants__user=obj)
        ).distinct().count()

        return {
            'saved_speech_cards_count': saved_cards_count,
            'completed_rehearsals_count': completed_rehearsals,
            'joined_meetings_count': joined_meetings_count,
        }

    def get_settings(self, obj):
        profile = getattr(obj, 'profile', None)
        return {
            'notification_enabled': profile.notification_enabled if profile else True,
            'preferred_language': profile.preferred_language if profile else '한국어',
        }