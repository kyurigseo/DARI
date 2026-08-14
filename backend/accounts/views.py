from rest_framework import generics, permissionsm, status

from .serializers import SignupSerializer, UserSerializer, MyPageResponseSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import UserProfile


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
    [마이페이지 종합 조회 API]
    GET: 현재 로그인된 사용자의 프로필, 활동 통계, 환경설정 반환
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if not hasattr(user, 'profile'):
            UserProfile.objects.create(user=user)

        serializer = MyPageResponseSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)