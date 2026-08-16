# WebSocket 연결용 JWT 인증 미들웨어
#
# 프론트엔드는 세션 쿠키가 아니라 localStorage에 저장한 JWT access 토큰으로 인증한다.
# 브라우저의 WebSocket API는 커스텀 Authorization 헤더를 지원하지 않으므로,
# 프론트에서 접속 시 쿼리스트링(?token=...)으로 access 토큰을 전달하고
# 여기서 검증해 scope['user']를 채워준다.

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def get_user_from_token(token_string):
    from django.contrib.auth import get_user_model

    User = get_user_model()

    try:
        validated_token = AccessToken(token_string)
        user_id = validated_token.get('user_id') or validated_token.get('user_id'.lower())
        return User.objects.get(id=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """?token=<access_token> 쿼리 파라미터로 전달된 JWT를 검증해 scope['user']를 설정한다."""

    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token_list = query_params.get('token')

        if token_list:
            scope['user'] = await get_user_from_token(token_list[0])
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
