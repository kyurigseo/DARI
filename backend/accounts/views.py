from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth import logout

from .models import UserProfile
from .serializers import (
    SignupSerializer,
    UserSerializer,
    MyPageResponseSerializer,
    UserProfileUpdateSerializer,
    UserSettingsUpdateSerializer
)


class SignupView(generics.CreateAPIView):
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class MyPageDetailView(APIView):
    """
    [마이페이지 API]
    - GET: 마이페이지 전체 데이터(프로필, 활동 통계 3종, 설정) 조회
    - PATCH / PUT: 정보 수정 모달을 통한 내 정보(이름, 직함/팀, 이메일, 프로필 사진) 수정
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        user = request.user
        if not hasattr(user, 'profile'):
            UserProfile.objects.create(user=user)

        serializer = MyPageResponseSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        user = request.user
        if not hasattr(user, 'profile'):
            UserProfile.objects.create(user=user)

        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response_serializer = MyPageResponseSerializer(user, context={'request': request})
            return Response(
                {
                    "message": "프로필 정보가 성공적으로 수정되었습니다.",
                    "data": response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        return self.patch(request)


class UserSettingsUpdateView(APIView):
    """
    [환경 설정 전용 API]
    - PATCH: 알림 받기 토글 On/Off 및 기본 번역 언어 변경
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserSettingsUpdateSerializer(profile, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "환경 설정이 성공적으로 변경되었습니다.",
                "settings": serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    [로그아웃 API]
    - POST: 세션 만료 및 JWT Refresh Token 블랙리스트 처리
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh_token') or request.data.get('refresh')
        if refresh_token:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass

        logout(request)
        return Response({
            "message": "성공적으로 로그아웃되었습니다."
        }, status=status.HTTP_200_OK)