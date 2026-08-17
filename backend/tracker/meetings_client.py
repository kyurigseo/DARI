"""
meetings 앱과의 유일한 연동 지점. meetings의 모델/코드는 절대 import하지 않고,
meetings가 이미 노출 중인 공개 계약만 호출한다:
  - POST /api/meetings/                            (CreateMeetingView)
  - POST /api/meetings/<room_code>/participants/    (ParticipantManageView)

meetings는 tracker와 같은 Django 프로세스에서 돌고 있어(INSTALLED_APPS에 함께 등록되어
동일 서버로 뜸), home/clients.py의 _call_internal_app와 동일하게 실제 소켓 통신 없이
django.test.Client로 공개 URL 계약만 태운다. 나중에 meetings가 별도 서비스로 분리되면
이 파일 내부(실제 HTTP 호출로 교체)만 바꾸면 되도록, tracker 쪽 함수 시그니처는 그대로
유지하는 것을 전제로 한다.

⚠️ 알려진 제약: meetings.CreateMeetingView는 title/room_code만 받고 예정 시각
(scheduled_start_time)이나 참가자 일괄 초대를 지원하지 않는다. 그래서 여기서는
1) 방을 즉시 생성하고 2) 참가자를 한 명씩 초대하는 방식으로 우회하며, "확정된 시각"
자체는 tracker.models.ScheduledMeetingRequest에 별도 보관한다. meetings 쪽에
scheduled_start_time 필드 + 참가자 일괄 등록을 추가해달라는 제안은 별도로 전달한다.
"""

import json
import uuid

from django.contrib.auth import get_user_model
from django.test import Client as DjangoTestClient

User = get_user_model()
_client = DjangoTestClient()


class MeetingsUnavailable(Exception):
    """meetings API 호출이 실패한 경우."""


def _auth_extra(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION")
    return {"HTTP_AUTHORIZATION": auth_header} if auth_header else {}


def generate_room_code(title):
    slug = "".join(ch for ch in title if ch.isalnum())[:12].lower() or "meeting"
    return f"{slug}-{uuid.uuid4().hex[:8]}"


def create_meeting(request, *, title, room_code):
    """제안 스펙과 무관하게, meetings에 이미 존재하는 POST /api/meetings/ 계약을 그대로 호출."""
    response = _client.post(
        "/api/meetings/",
        data=json.dumps({"title": title, "room_code": room_code}),
        content_type="application/json",
        SERVER_NAME=request.get_host().split(":", 1)[0],
        **_auth_extra(request),
    )
    if response.status_code != 201:
        raise MeetingsUnavailable(f"POST /api/meetings/ -> {response.status_code}: {response.content!r}")
    return json.loads(response.content)


def invite_participant(request, *, room_code, user_id):
    """meetings에 이미 존재하는 POST /api/meetings/<room_code>/participants/ 계약을 호출.
    이 엔드포인트는 user_id가 아니라 username을 받으므로 여기서 조회해서 넘긴다."""
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise MeetingsUnavailable(f"unknown user_id={user_id}")

    response = _client.post(
        f"/api/meetings/{room_code}/participants/",
        data=json.dumps({"username": user.username}),
        content_type="application/json",
        SERVER_NAME=request.get_host().split(":", 1)[0],
        **_auth_extra(request),
    )
    if response.status_code != 200:
        raise MeetingsUnavailable(
            f"POST /api/meetings/{room_code}/participants/ -> {response.status_code}: {response.content!r}"
        )
    return json.loads(response.content)
