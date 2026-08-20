import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import MeetingSession, MeetingParticipant, MeetingTranscript, MeetingChatMessage
from .services import AIServicePipeline
from django.utils import timezone

class MeetingConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audio_buffer = bytearray()
        self.audio_chunk_count = 0

    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'meeting_{self.room_code}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        meeting_status = await self.get_meeting_status()
        if meeting_status is None or meeting_status == 'ENDED':
            await self.close()
            return

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

    async def receive_bytes(self, bytes_data):
        audio_size = len(bytes_data)

        print(f"🎤 [STT 요청] {audio_size} 바이트 수신")

        # 너무 짧은 오디오 chunk는 STT에 보내지 않음
        if audio_size < 1000:
            print("⚠️ [STT 무시] 오디오 데이터가 너무 짧음")
            return

        original_text = await AIServicePipeline.process_stt(bytes_data)

        if not original_text:
            return

        print(f"📝 [STT 결과] {original_text}")

        target_langs = ['KO', 'EN-US', 'JA', 'ZH', 'DE']
        translations = await AIServicePipeline.process_translation(
            original_text,
            target_langs
        )

        await self.save_transcript(original_text, translations)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'subtitle_broadcast',
                'speaker_id': self.user.id,
                'speaker_name': self.user.username,
                'original_text': original_text,
                'translations': translations
            }
        )

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data is not None:
            await self.receive_bytes(bytes_data)
            return

        if text_data is None:
            return

        data = json.loads(text_data)
        event_type = data.get('type')

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

        elif event_type == 'chat_message':
            message = data.get('message')
            is_speech_card = data.get('is_speech_card', False)

            if message:
                await self.save_chat_message(message, is_speech_card)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_broadcast',
                        'sender_id': self.user.id,
                        'sender_name': self.user.username,
                        'message': message,
                        'is_speech_card': is_speech_card,
                    }
                )

    async def chat_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'message': event['message'],
            'is_speech_card': event['is_speech_card'],
        }, default=str))

    async def subtitle_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'subtitle',
            'speaker_id': event['speaker_id'],
            'speaker_name': event['speaker_name'],
            'original_text': event['original_text'],
            'translations': event['translations']
        }, default=str))

    async def user_joined(self, event):
        await self.send(text_data=json.dumps(event, default=str))

    async def user_left(self, event):
        await self.send(text_data=json.dumps(event, default=str))

    async def webrtc_signal(self, event):
        if event['sender_id'] != self.user.id:
            await self.send(text_data=json.dumps(event['signal_data'], default=str))

    async def status_changed(self, event):
        await self.send(text_data=json.dumps(event, default=str))

    async def kicked(self, event):
        if event['user_id'] is not None and str(event['user_id']) == str(self.user.id):
            await self.send(text_data=json.dumps({'type': 'kicked'}))
            await self.close()

    @database_sync_to_async
    def get_meeting_status(self):
        return MeetingSession.objects.filter(room_code=self.room_code).values_list('status', flat=True).first()

    @database_sync_to_async
    def save_chat_message(self, message, is_speech_card):
        meeting_id = MeetingSession.objects.filter(room_code=self.room_code).values_list('id', flat=True).first()
        if meeting_id:
            MeetingChatMessage.objects.create(
                meeting_id=meeting_id,
                sender=self.user,
                message=message,
                is_speech_card=is_speech_card
            )

    @database_sync_to_async
    def save_transcript(self, original_text, translations):
        meeting_id = MeetingSession.objects.filter(room_code=self.room_code).values_list('id', flat=True).first()
        if meeting_id:
            MeetingTranscript.objects.create(
                meeting_id=meeting_id,
                speaker=self.user,
                original_text=original_text,
                translations=translations
            )

    @database_sync_to_async
    def set_participant_active_status(self, is_active):
        meeting = MeetingSession.objects.only(
            'id',
            'host_id'
        ).filter(
            room_code=self.room_code
        ).first()

        if not meeting:
            return

        participant, _ = MeetingParticipant.objects.get_or_create(
            meeting_id=meeting.id,
            user=self.user,
            defaults={
                'is_host': meeting.host_id == self.user.id,
            }
        )

        now = timezone.now()

        participant.is_active = is_active

        if is_active:
            # 회의에 새로 들어온 시각
            if participant.joined_at is None:
                participant.joined_at = now

            participant.left_at = None

            participant.save(
                update_fields=[
                    'is_active',
                    'joined_at',
                    'left_at',
                ]
            )

        else:
            # 회의에서 나간 시각
            participant.left_at = now

            participant.save(
                update_fields=[
                    'is_active',
                    'left_at',
                ]
            )

    @database_sync_to_async
    def update_participant_media_status(self, is_mic_on, is_camera_on, is_speaking):
        participant = MeetingParticipant.objects.filter(
            meeting__room_code=self.room_code,
            user=self.user
        ).first()

        if participant:
            update_fields = []
            if is_mic_on is not None:
                participant.is_mic_on = is_mic_on
                update_fields.append('is_mic_on')
            if is_camera_on is not None:
                participant.is_camera_on = is_camera_on
                update_fields.append('is_camera_on')
            if is_speaking is not None:
                participant.is_speaking = is_speaking
                update_fields.append('is_speaking')

            if update_fields:
                participant.save(update_fields=update_fields)