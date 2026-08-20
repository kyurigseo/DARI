# 회의실 생성, 대기실 조회, 토큰 발급 API
import threading
import urllib.parse
from django.db import models
from django.conf import settings
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from cards.models import Card
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import MeetingSession, MeetingParticipant, SpeechCard, MeetingChatMessage, MeetingSummary, MeetingMemo, ActionItem
from .utils import generate_media_server_token
from .services import MeetingSummaryPipeline, MeetingShareFormatter
from .serializers import (
    MeetingSessionSerializer,
    ParticipantSerializer,
    SpeechCardSerializer,
    MeetingChatMessageSerializer,
    MeetingSummaryTabSerializer,
    MeetingMemoSerializer,
    ActionItemSerializer
)

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

        response_data = {
            'room_code': meeting.room_code,
            'title': meeting.title,
            'host_id': str(meeting.host_id),
            'status': meeting.status,
            'participants_count': active_participants.count(),
            'participants': ParticipantSerializer(active_participants, many=True).data
        }
        if settings.DARI_DEMO_MODE and meeting.room_code.startswith('demo-'):
            response_data['chat_history'] = [
                {
                    'id': str(message.id),
                    'sender_id': str(message.sender_id),
                    'sender_name': message.sender.username,
                    'message': message.message,
                    'is_speech_card': message.is_speech_card,
                }
                for message in meeting.chat_messages.select_related('sender').all()
            ]
            response_data['transcript_history'] = [
                {
                    'id': str(transcript.id),
                    'speaker_id': str(transcript.speaker_id),
                    'speaker_name': transcript.speaker.username,
                    'original_text': transcript.original_text,
                    'translations': transcript.translations,
                }
                for transcript in meeting.transcripts.select_related('speaker').all()
            ]
        return Response(response_data)


class MediaTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_code):
        return self._issue_token(request, room_code)

    def post(self, request, room_code):
        return self._issue_token(request, room_code)

    def _issue_token(self, request, room_code):
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
        cards = Card.objects.filter(owner=request.user)
        return Response([
            {
                'id': str(card.id),
                'persona_name': card.partner_tag,
                'situation': card.situation_label,
                'korean_script': card.text_ko,
                'translated_script': card.text_translated,
                'target_lang': card.language_code.upper(),
                'created_at': card.created_at,
            }
            for card in cards
        ], status=status.HTTP_200_OK)


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
        if not participant.is_active:
            participant.is_active = True
            participant.save(update_fields=['is_active'])
        return Response({
            'message': f'{username} 님을 회의에 초대했습니다.',
            'participant': ParticipantSerializer(participant).data,
        }, status=status.HTTP_200_OK)


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

            # 실시간으로 연결되어 있는 대상 참가자의 WebSocket에 강퇴 신호를 보내
            # 클라이언트가 즉시 통화를 종료하도록 한다.
            channel_layer = get_channel_layer()
            if channel_layer is not None:
                async_to_sync(channel_layer.group_send)(
                    f'meeting_{room_code}',
                    {
                        'type': 'kicked',
                        'user_id': target_user_id,
                    }
                )

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
        meeting.ended_at = timezone.now()
        meeting.save(update_fields=['status', 'ended_at'])
        if settings.DARI_DEMO_MODE:
            MeetingSummaryPipeline.generate_summary_and_action_items(meeting.id)
        else:
            threading.Thread(
                target=MeetingSummaryPipeline.generate_summary_and_action_items,
                args=(meeting.id,)
            ).start()

        return Response({
            'message': '회의가 성공적으로 종료되었으며, AI 요약 생성이 시작되었습니다.',
            'room_code': meeting.room_code,
            'status': meeting.status
        }, status=status.HTTP_200_OK)

class UserMeetingListView(APIView):
    """
    [상단 탭 UI용 회의 목록 조회 API]
    사용자가 호스트이거나 참가했던 회의 목록 반환
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        meetings = MeetingSession.objects.filter(
            models.Q(host=user) | models.Q(participants__user=user)
        ).filter(status='ENDED').distinct().order_by('-created_at')

        serializer = MeetingSummaryTabSerializer(meetings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MeetingReportDetailView(APIView):
    """
    [특정 회의 상세 리포트 조회 API]
    - 회의 기본 정보 및 상단 타이틀
    - AI 요약문
    - 본인이 작성한 메모 리스트
    - 회의의 Action Item 리스트
    - 회의 참가자 명단 (담당자 지정 모달 연동용)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, room_code):
        meeting = get_object_or_404(MeetingSession, room_code=room_code)


        summary_obj = getattr(meeting, 'summary', None)
        summary_content = summary_obj.content if summary_obj else "아직 생성된 회의 요약이 없습니다."

        memos = MeetingMemo.objects.filter(meeting=meeting, user=request.user)
        memo_serializer = MeetingMemoSerializer(memos, many=True)

        action_items = ActionItem.objects.filter(meeting=meeting)
        action_item_serializer = ActionItemSerializer(action_items, many=True)

        participants_data = []
        participants_data.append({
            'name': request.user.username if meeting.host == request.user else meeting.host.username,
            'is_host': True,
            'is_me': meeting.host == request.user
        })
        for p in meeting.participants.exclude(user=meeting.host):
            participants_data.append({
                'name': p.user.username,
                'is_host': False,
                'is_me': p.user == request.user
            })

        return Response({
            'room_code': meeting.room_code,
            'title': meeting.title,
            'display_header': f"{meeting.title} · {meeting.created_at.month}/{meeting.created_at.day}",
            'ai_summary': summary_content,
            'memos': memo_serializer.data,
            'action_items': action_item_serializer.data,
            'participants': participants_data
        }, status=status.HTTP_200_OK)


class MeetingMemoListCreateView(APIView):
    """
    [메모 목록 조회 및 작성 API]
    GET: 해당 회의에 내가 쓴 메모 목록
    POST: 새 메모 작성 저장
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, room_code):
        meeting = get_object_or_404(MeetingSession, room_code=room_code)
        memos = MeetingMemo.objects.filter(meeting=meeting, user=request.user)
        serializer = MeetingMemoSerializer(memos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, room_code):
        meeting = get_object_or_404(MeetingSession, room_code=room_code)
        content = request.data.get('content', '').strip()

        if not content:
            return Response({'error': '메모 내용을 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        memo = MeetingMemo.objects.create(
            meeting=meeting,
            user=request.user,
            content=content
        )
        serializer = MeetingMemoSerializer(memo)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MeetingMemoDeleteView(APIView):
    """
    [메모 삭제 API]
    메모 우측 x 버튼 클릭 시 삭제 처리
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, memo_id):
        memo = get_object_or_404(MeetingMemo, id=memo_id, user=request.user)
        memo.delete()
        return Response({'message': '메모가 삭제되었습니다.'}, status=status.HTTP_200_OK)


class ActionItemUpdateView(APIView):
    """
    [Action Item 수정 API (PATCH)]
    - 완료 체크박스 상태 토글 (`is_completed`)
    - 담당자 변경 (`assignee`)
    - 마감 기한 변경 (`due_date`: "YYYY-MM-DD" 또는 null)
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id):
        action_item = get_object_or_404(ActionItem, id=item_id)
        data = request.data
        if 'is_completed' in data:
            action_item.is_completed = bool(data['is_completed'])

        if 'assignee' in data:
            action_item.assignee = str(data['assignee']).strip() or '미지정'

        if 'due_date' in data:
            due_date_val = data['due_date']
            action_item.due_date = due_date_val if due_date_val else None

        action_item.save()
        serializer = ActionItemSerializer(action_item)
        return Response(serializer.data, status=status.HTTP_200_OK)

class MeetingShareTextView(APIView):
    """
    [Slack / 클립보드 복사 및 mailto 생성 API]
    - formatted_text: 슬랙이나 메모장에 붙여넣을 완성된 텍스트
    - mailto_link: 클릭 시 이메일 앱(Outlook, 기본 메일 앱)을 띄우는 링크 파라미터
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, room_code):
        meeting = get_object_or_404(MeetingSession, room_code=room_code)

        formatted_text = MeetingShareFormatter.generate_formatted_text(meeting, request.user)

        email_subject = f"[DARI] {meeting.title} 회의 요약 및 Action Items"
        encoded_subject = urllib.parse.quote(email_subject)
        encoded_body = urllib.parse.quote(formatted_text)
        mailto_link = f"mailto:?subject={encoded_subject}&body={encoded_body}"

        return Response({
            'meeting_title': meeting.title,
            'formatted_text': formatted_text,
            'mailto_link': mailto_link
        }, status=status.HTTP_200_OK)


class MeetingEmailSendView(APIView):
    """
    [Django SMTP 기반 회의 결과 이메일 직접 전송 API]
    - 참석자 전원 또는 입력받은 이메일 목록으로 전송
    - 전송 실패 시 예외 처리 및 에러 안내
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, room_code):
        meeting = get_object_or_404(MeetingSession, room_code=room_code)
        target_emails = request.data.get('emails', [])

        if not target_emails:
            participant_emails = [
                p.user.email for p in meeting.participants.all() if p.user.email
            ]
            if meeting.host.email:
                participant_emails.append(meeting.host.email)
            target_emails = list(set(participant_emails))

        if not target_emails:
            return Response(
                {'error': '결과를 전송할 이메일 주소가 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        formatted_text = MeetingShareFormatter.generate_formatted_text(meeting, request.user)
        subject = f"[DARI] {meeting.title} 회의 요약 및 Action Items"

        try:
            send_mail(
                subject=subject,
                message=formatted_text,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@dari.com'),
                recipient_list=target_emails,
                fail_silently=False,
            )
            return Response({
                'message': f'{len(target_emails)}명에게 회의 결과가 성공적으로 전송되었습니다.',
                'sent_to': target_emails
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': '이메일 전송 중 오류가 발생했습니다. 네트워크 상태를 확인하고 잠시 후 다시 시도해 주세요.',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HomeMeetingListView(APIView):
    """
    [홈 화면 API]
    내가 참여 예정이거나 대기 중인(WAITING) 회의 목록만 조회
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        meetings = MeetingSession.objects.filter(
            (models.Q(host=request.user) | models.Q(participants__user=request.user)),
            status='WAITING'
        ).distinct().order_by('-created_at')

        serializer = MeetingSessionSerializer(meetings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class InvitationListView(APIView):
    """
    [받은 회의 초대 목록 조회 API]
    종 모양 알림 아이콘을 눌렀을 때 'PENDING(대기 중)' 상태인 초대 목록 반환
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        invitations = MeetingParticipant.objects.filter(user=request.user, status='PENDING')
        data = []
        for inv in invitations:
            data.append({
                "meeting_id": inv.meeting.id,
                "room_code": inv.meeting.room_code,
                "title": inv.meeting.title,
                "host_name": inv.meeting.host.username if inv.meeting.host else "호스트",
                "created_at": inv.meeting.created_at,
            })
        return Response(data, status=status.HTTP_200_OK)


class RespondInvitationView(APIView):
    """
    [회의 초대 수락 / 거절 처리 API]
    POST 요청으로 {"action": "accept"} 또는 {"action": "reject"} 전달
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, meeting_id):
        action = request.data.get('action')

        participant = get_object_or_404(MeetingParticipant, meeting_id=meeting_id, user=request.user)

        if action == 'accept':
            participant.status = 'ACCEPTED'
            participant.is_active = True
            participant.save(update_fields=['status', 'is_active'])
            return Response({'message': '회의 참가가 수락되었습니다.'}, status=status.HTTP_200_OK)

        elif action == 'reject':
            participant.status = 'REJECTED'
            participant.is_active = False
            participant.save(update_fields=['status', 'is_active'])
            return Response({'message': '회의 로그가 거절되었습니다.'}, status=status.HTTP_200_OK)

        else:
            return Response({'error': '올바르지 않은 요청입니다. (action: accept/reject 필요)'}, status=status.HTTP_400_BAD_REQUEST)
