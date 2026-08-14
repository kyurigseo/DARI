# 회의실 생성, 대기실 조회, 토큰 발급 API
import threading
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import MeetingSession, MeetingParticipant, SpeechCard, MeetingChatMessage
from .serializers import MeetingSessionSerializer, ParticipantSerializer, SpeechCardSerializer, MeetingChatMessageSerializer
from .utils import generate_media_server_token
from .services import MeetingSummaryPipeline

User = get_user_model()

class CreateMeetingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
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
        meeting = get_object_or_404(MeetingSession, room_code=room_code)
        token = generate_media_server_token(
            room_code=meeting.room_code,
            user_id=request.user.id,
            username=request.user.username
        )
        return Response({'token': token})


class SpeechCardListView(APIView):
    """발언카드 조회 API: 로그인 사용자가 사전에 생성한 발언카드 목록 반환"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cards = SpeechCard.objects.filter(user=request.user)
        serializer = SpeechCardSerializer(cards, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ParticipantManageView(APIView):
    """참가자 관리 API: 목록 조회 및 사용자 초대"""
    permission_classes = [IsAuthenticated]

    def get(self, request, room_code):
        meeting = get_object_or_404(MeetingSession, room_code=room_code)
        participants = meeting.participants.filter(is_active=True)
        return Response(ParticipantSerializer(participants, many=True).data)

    def post(self, request, room_code):
        """사용자 초대 API"""
        meeting = get_object_or_404(MeetingSession, room_code=room_code)
        username = request.data.get('username')

        invited_user = User.objects.filter(username=username).first()
        if not invited_user:
            return Response({'error': '존재하지 않는 사용자입니다.'}, status=status.HTTP_404_NOT_FOUND)

        participant, created = MeetingParticipant.objects.get_or_create(
            meeting=meeting,
            user=invited_user,
            defaults={'is_host': False}
        )
        return Response({'message': f'{username} 님을 회의에 초대했습니다.'}, status=status.HTTP_200_OK)


class KickParticipantView(APIView):
    """호스트 권한 참가자 내보내기 API"""
    permission_classes = [IsAuthenticated]

    def post(self, request, room_code):
        meeting = get_object_or_404(MeetingSession, room_code=room_code)

        # 호스트 권한 체크
        if meeting.host != request.user:
            return Response({'error': '참가자를 내보낼 권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        target_user_id = request.data.get('user_id')
        participant = MeetingParticipant.objects.filter(meeting=meeting, user_id=target_user_id).first()

        if participant:
            participant.is_active = False
            participant.save()
            return Response({'message': '참가자를 회의에서 내보냈습니다.'}, status=status.HTTP_200_OK)

        return Response({'error': '해당 참가자를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

class EndMeetingView(APIView):
    """
    [회의 종료 API]
    호스트 권한으로 회의를 종료하고, 백그라운드에서 AI 요약 & Action Item 파이프라인을 실행
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, room_code):
        meeting = get_object_or_404(MeetingSession, room_code=room_code)

        if meeting.host != request.user:
            return Response({'error': '회의를 종료할 권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        meeting.status = 'ENDED'
        meeting.save()
        threading.Thread(
            target=MeetingSummaryPipeline.generate_summary_and_action_items,
            args=(meeting.id,)
        ).start()

        return Response({
            'message': '회의가 성공적으로 종료되었으며, AI 요약 생성이 시작되었습니다.',
            'room_code': meeting.room_code,
            'status': meeting.status
        }, status=status.HTTP_200_OK)