from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import UserProfile
from .serializers import (
    SignupSerializer,
    UserSerializer,
    MyPageResponseSerializer,
    UserProfileUpdateSerializer
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
    [마이페이지 종합 API]
    - GET: 현재 로그인된 사용자의 프로필, 활동 통계, 환경설정 반환
    - PATCH / PUT: 내 정보 수정 모달 데이터 업데이트 (이름, 직함·팀, 이메일, 프로필 사진)
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