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
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        serializer = MyPageResponseSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response_serializer = MyPageResponseSerializer(request.user, context={'request': request})
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
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        serializer = UserSettingsUpdateSerializer(request.user.profile, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "환경 설정이 성공적으로 변경되었습니다.",
                "settings": serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
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