from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import UserProfile
from meetings.models import MeetingSession, SpeechCard

User = get_user_model()


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


class MyPageResponseSerializer(serializers.ModelSerializer):
    """
    [마이페이지 종합 조회용]
    - 프로필 정보: 이름, 이메일, 직함·팀, 사진
    - 활동 통계: 발언카드 수, 리허설 완료 수, 참여 회의 수
    - 환경 설정: 알림 수신 여부, 기본 번역 언어
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
        # 1. 저장한 발언카드 수
        saved_cards_count = SpeechCard.objects.filter(user=obj).count() if hasattr(SpeechCard, 'user') else SpeechCard.objects.count()
        # 2. 완료한 리허설 수
        completed_rehearsals = getattr(obj.profile, 'completed_rehearsals_count', 0) if hasattr(obj, 'profile') else 0
        # 3. 참여한 회의 수 (호스트 or 참가자)
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


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    [내 정보 수정 모달용]
    - User: username(이름), email(이메일)
    - UserProfile: position_team(직함·팀), profile_image(사진)
    """
    name = serializers.CharField(source='username', required=False)
    email = serializers.EmailField(required=False)
    position_team = serializers.CharField(source='profile.position_team', required=False, allow_blank=True)
    profile_image = serializers.ImageField(source='profile.profile_image', required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['name', 'email', 'position_team', 'profile_image']

    def validate_email(self, value):
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("이미 사용 중인 이메일 주소입니다.")
        return value

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})

        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.save()

        profile, _ = UserProfile.objects.get_or_create(user=instance)
        if 'position_team' in profile_data:
            profile.position_team = profile_data['position_team']
        if 'profile_image' in profile_data:
            profile.profile_image = profile_data['profile_image']
        profile.save()

        return instance


class UserSettingsUpdateSerializer(serializers.ModelSerializer):
    """
    [환경 설정 변경용]
    - notification_enabled: 알림 받기 토글
    - preferred_language: 기본 번역 선호 언어
    """
    class Meta:
        model = UserProfile
        fields = ['notification_enabled', 'preferred_language']
        extra_kwargs = {
            'notification_enabled': {'required': False},
            'preferred_language': {'required': False},
        }

