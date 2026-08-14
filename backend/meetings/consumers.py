import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import MeetingSession, MeetingParticipant, MeetingTranscript
from .services import AIServicePipeline

class MeetingConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audio_buffer = bytearray()

    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'meeting_{self.room_code}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
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

    async def disconnect(self, close_code):
        await self.set_participant_active_status(False)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)


    async def receive_bytes(self, bytes_data):
        """프론트엔드에서 전송한 오디오 바이너리 조각(Audio Chunk) 수신"""
        self.audio_buffer.extend(bytes_data)

        # 적절한 버퍼 크기 축적 시 STT/번역 실행
        if len(self.audio_buffer) >= 64 * 1024:
            chunk_to_process = bytes(self.audio_buffer)
            self.audio_buffer.clear()

            original_text = await AIServicePipeline.process_stt(chunk_to_process)

            if original_text:
                # 실시간 번역 진행
                target_langs = ['KO', 'EN-US', 'JA', 'ZH', 'DE']
                translations = await AIServicePipeline.process_translation(original_text, target_langs)

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


    async def receive(self, text_data):
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


    async def subtitle_broadcast(self, event):
        """회의실 내 전원에게 원문 및 번역 자막 전송"""
        await self.send(text_data=json.dumps({
            'type': 'subtitle',
            'speaker_id': event['speaker_id'],
            'speaker_name': event['speaker_name'],
            'original_text': event['original_text'],
            'translations': event['translations']
        }))

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
    def save_transcript(self, original_text, translations):
        meeting = MeetingSession.objects.filter(room_code=self.room_code).first()
        if meeting:
            MeetingTranscript.objects.create(
                meeting=meeting,
                speaker=self.user,
                original_text=original_text,
                translations=translations
            )

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