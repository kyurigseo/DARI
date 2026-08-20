# 미디어 서버 JWT 토큰 생성 유틸리티

import datetime
import jwt
from django.conf import settings

def generate_media_server_token(room_code: str, user_id: str, username: str) -> str:
    """
    미디어 서버(예: LiveKit) 접속을 위한 JWT 토큰 발급
    """
    secret = getattr(settings, 'MEDIA_SERVER_SECRET', 'fallback_secret_key')
    payload = {
        'room': room_code,
        'identity': str(user_id),
        'name': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2),
        'video': True,
        'audio': True,
    }
    token = jwt.encode(payload, secret, algorithm='HS256')
    return token