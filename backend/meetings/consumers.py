# WebRTC 시그널링 & 상태 동기화 WebSocket Consumer

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import MeetingSession, MeetingParticipant

class MeetingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'meeting_{self.room_code}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        # 회의실 그룹 가입
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.set_participant_active_status(True)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )

    async def disconnect(self, close_code):
        # 소켓 연결 끊김 시 비정상 종료 대응
        await self.set_participant_active_status(False)

        # 그룹 알림
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )

        # 회의실 그룹 탈퇴
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """클라이언트 메시지 수신 및 분기"""
        data = json.loads(text_data)
        event_type = data.get('type')

        # WebRTC 시그널링 중계 (Offer, Answer, ICE Candidate)
        if event_type in ['offer', 'answer', 'candidate']:
            target_id = data.get('target_id')
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_signal',
                    'sender_id': self.user.id,
                    'target_id': target_id,
                    'signal_data': data,
                }
            )

        # 실시간 상태 업데이트 (마이크, 카메라, 발언 여부)
        elif event_type == 'status_update':
            is_mic_on = data.get('is_mic_on')
            is_camera_on = data.get('is_camera_on')
            is_speaking = data.get('is_speaking')

            await self.update_participant_media_status(is_mic_on, is_camera_on, is_speaking)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'status_changed',
                    'user_id': self.user.id,
                    'is_mic_on': is_mic_on,
                    'is_camera_on': is_camera_on,
                    'is_speaking': is_speaking,
                }
            )


    async def user_joined(self, event):
        await self.send(text_data=json.dumps(event))

    async def user_left(self, event):
        await self.send(text_data=json.dumps(event))

    async def webrtc_signal(self, event):
        if event['sender_id'] != self.user.id:
            await self.send(text_data=json.dumps(event['signal_data']))

    async def status_changed(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def set_participant_active_status(self, is_active):
        meeting = MeetingSession.objects.filter(room_code=self.room_code).first()
        if meeting:
            participant, _ = MeetingParticipant.objects.get_or_create(
                meeting=meeting,
                user=self.user,
                defaults={'is_host': meeting.host == self.user}
            )
            participant.is_active = is_active
            participant.save()

    @database_sync_to_async
    def update_participant_media_status(self, is_mic_on, is_camera_on, is_speaking):
        meeting = MeetingSession.objects.filter(room_code=self.room_code).first()
        if meeting:
            participant = MeetingParticipant.objects.filter(meeting=meeting, user=self.user).first()
            if participant:
                if is_mic_on is not None:
                    participant.is_mic_on = is_mic_on
                if is_camera_on is not None:
                    participant.is_camera_on = is_camera_on
                if is_speaking is not None:
                    participant.is_speaking = is_speaking
                participant.save()