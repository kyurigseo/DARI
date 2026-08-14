# meetings 앱 전용 WebSocket URL 라우팅

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # meetings/ws/room_code/ 형태로 접속
    re_path(r'ws/meetings/(?P<room_code>[\w-]+)/$', consumers.MeetingConsumer.as_asgi()),
]