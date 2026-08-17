"""
ASGI config for dari project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dari.settings")

from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
import meetings.routing
from meetings.channels_auth import JWTAuthMiddlewareStack

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # 프론트는 JWT(access token)로 인증하므로 세션 기반 AuthMiddlewareStack 대신
    # 쿼리스트링(?token=...)의 JWT를 검증하는 JWTAuthMiddlewareStack을 사용한다.
    "websocket": JWTAuthMiddlewareStack(
        URLRouter(
            meetings.routing.websocket_urlpatterns
        )
    ),
})
