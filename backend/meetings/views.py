# 회의실 생성, 대기실 조회, 토큰 발급 API

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import MeetingSession, MeetingParticipant
from .serializers import MeetingSessionSerializer, ParticipantSerializer
from .utils import generate_media_server_token

class CreateMeetingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """회의실 생성 API"""
        title = request.data.get('title', '신규 회의')
        room_code = request.data.get('room_code')

        if MeetingSession.objects.filter(room_code=room_code).exists():
            return Response({'error': '이미 존재하는 회의 코드입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        meeting = MeetingSession.objects.create(
            room_code=room_code,
            title=title,
            host=request.user
        )
        return Response(MeetingSessionSerializer(meeting).data, status=status.HTTP_201_CREATED)


class PrejoinView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_code):
        """대기실 정보 조회 및 유효성 검증 API"""
        meeting = get_object_or_404(MeetingSession, room_code=room_code)

        if meeting.status == 'ENDED':
            return Response({'error': '이미 종료된 회의입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        active_participants = meeting.participants.filter(is_active=True)

        return Response({
            'room_code': meeting.room_code,
            'title': meeting.title,
            'status': meeting.status,
            'participants_count': active_participants.count(),
            'participants': ParticipantSerializer(active_participants, many=True).data
        })


class MediaTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_code):
        """미디어 서버/시그널링 접속용 토큰 발급 API"""
        meeting = get_object_or_404(MeetingSession, room_code=room_code)
        token = generate_media_server_token(
            room_code=meeting.room_code,
            user_id=request.user.id,
            username=request.user.username
        )
        return Response({'token': token})