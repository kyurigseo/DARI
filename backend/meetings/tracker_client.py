"""
meetings 앱에서 tracker의 participation ingest API를 호출하기 위한 내부 클라이언트.

meetings와 tracker가 현재 동일한 Django 프로세스에서 실행되므로
실제 외부 HTTP 통신 대신 Django test Client를 이용해 공개 URL 계약을 호출한다.

tracker가 추후 별도 서비스로 분리될 경우 이 파일의 호출 방식만
실제 HTTP 요청으로 교체하면 된다.
"""

import json

from django.conf import settings
from django.test import Client as DjangoTestClient


_client = DjangoTestClient()


class TrackerUnavailable(Exception):
    """tracker API 호출이 실패한 경우."""


def ingest_participation(
    request,
    *,
    external_meeting_id,
    meeting_title,
    meeting_time_utc,
    participants,
):
    """
    tracker의 POST /api/v1/tracker/participation/ingest/ 호출.

    participants 예시:
    [
        {
            "user_id": "<uuid>",
            "local_timezone": "Asia/Seoul",
            "local_region": "Seoul, KR",
            "speaking_duration_seconds": 0,
        },
        ...
    ]
    """

    token = getattr(settings, "INTERNAL_SERVICE_TOKEN", "")

    if not token:
        raise TrackerUnavailable(
            "INTERNAL_SERVICE_TOKEN이 설정되어 있지 않습니다."
        )

    payload = {
        "external_meeting_id": external_meeting_id,
        "meeting_title": meeting_title,
        "meeting_time_utc": meeting_time_utc.isoformat(),
        "participants": participants,
    }

    response = _client.post(
        "/api/v1/tracker/participation/ingest/",
        data=json.dumps(payload),
        content_type="application/json",
        SERVER_NAME=request.get_host().split(":", 1)[0],
        HTTP_AUTHORIZATION=f"Internal {token}",
    )

    if response.status_code != 201:
        raise TrackerUnavailable(
            "POST /api/v1/tracker/participation/ingest/ "
            f"-> {response.status_code}: {response.content!r}"
        )

    return json.loads(response.content)