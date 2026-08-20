"""
home 앱은 다른 앱의 모델/DB를 직접 건드리지 않고, 각 앱이 제공하는 API 계약을 통해서만
데이터를 모은다. 아직 없는 API는 mocks.py의 목업으로 대체하고, 실제 엔드포인트가 생기면
아래 fetch_* 함수 내부의 호출부만 실 엔드포인트로 바꾸면 되도록 구조를 맞췄다.

- rehearsal / cards / tracker: home과 같은 Django 프로세스에서 도는 A 담당 앱이므로,
  실제 소켓 통신 없이 Django 테스트 클라이언트로 해당 앱의 공개 URL을 그대로 호출한다
  (모델 import/조인 없이 URL 계약만 탄다는 원칙은 그대로 지켜짐).
- meetings / summary: B 담당이며 별도 서비스로 분리될 가능성이 있어 설정된 BASE_URL로
  실제 HTTP 호출을 시도한다. BASE_URL이 없으면(아직 미설정) 바로 목업으로 폴백한다.
"""

import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.test import Client as DjangoTestClient
from django.utils import timezone

from . import mocks

_internal_client = DjangoTestClient()

# 참가 버튼을 활성화할 여유 시간(회의 시작 전 몇 분부터 "참가 가능"으로 볼지)
JOIN_WINDOW_BEFORE_START = timedelta(minutes=10)


class UpstreamUnavailable(Exception):
    """다른 앱 API 호출이 실패했거나 아직 구현되지 않은 경우."""


def _call_internal_app(path, request):
    """같은 프로세스에서 도는 A 담당 앱(rehearsal/cards/tracker)의 공개 API를 호출."""
    auth_header = request.META.get("HTTP_AUTHORIZATION")
    extra = {"HTTP_AUTHORIZATION": auth_header} if auth_header else {}
    # django.test.Client의 기본 HTTP_HOST는 "testserver"인데, 운영 중인 서버의
    # ALLOWED_HOSTS에는 없는 값이라 CommonMiddleware가 400으로 거부한다.
    # DEBUG=True에서는 Django가 127.0.0.1을 항상 허용하므로 여기에 고정한다.
    response = _internal_client.get(path, SERVER_NAME="127.0.0.1", **extra)
    if response.status_code >= 400:
        raise UpstreamUnavailable(f"{path} -> {response.status_code}")
    return json.loads(response.content)


def _call_external_service(base_url_setting, path, timeout=2):
    """B 담당 앱(meetings/summary)의 API를 실제 HTTP로 호출. BASE_URL 미설정 시 즉시 실패."""
    base_url = getattr(settings, base_url_setting, None)
    if not base_url:
        raise UpstreamUnavailable(f"{base_url_setting} not configured")
    token = getattr(settings, "INTERNAL_SERVICE_TOKEN", "")
    req = urllib.request.Request(base_url.rstrip("/") + path)
    if token:
        req.add_header("Authorization", f"Internal {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise UpstreamUnavailable(str(exc)) from exc


def fetch_today_meetings(request):
    """
    meetings 앱이 현재 동일한 Django 프로젝트 내에 구현되어 있으므로,
    _call_internal_app을 사용해 내부 API(/api/meetings/home/)를 직접 호출합니다.
    """
    if settings.DARI_DEMO_MODE:
        from meetings.models import MeetingSession
        demo_meetings = (
            MeetingSession.objects.filter(
                models.Q(host=request.user) | models.Q(participants__user=request.user),
                room_code__startswith="demo-",
            )
            .distinct()
            .order_by("created_at")
        )
        results = [
            {
                "meeting_id": str(meeting.id),
                "room_code": meeting.room_code,
                "title": meeting.title,
                "start_time": meeting.created_at.isoformat(),
                "end_time": (meeting.created_at + timedelta(hours=1)).isoformat(),
                "participant_count": meeting.participants.filter(is_active=True).count(),
                "join_url": f"/meeting/{meeting.room_code}",
                "joinable": meeting.status != "ENDED",
            }
            for meeting in demo_meetings
            if meeting.status != "ENDED"
        ]
        return {"count": len(results), "results": results, "source": "demo"}

    try:
        raw_meetings = _call_internal_app("/api/meetings/home/", request)
        source = "live"
    except Exception as e:
        print(f"[Home API 연동 오류] {e}")
        raw_meetings = mocks.MOCK_TODAY_MEETINGS
        source = "mock"

    now = timezone.now()
    enriched = []

    for m in raw_meetings:
        if source == "live":
            start_str = m.get("created_at") or now.isoformat()
            start = _parse_iso(start_str)
            room_code = m.get("room_code", "")

            enriched.append({
                "meeting_id": m.get("id"),
                "room_code": room_code,
                "title": m.get("title", "새로운 회의"),
                "start_time": start_str,
                "end_time": (start + timedelta(hours=1)).isoformat() if start else None,
                "participant_count": m.get("participants_count", 1),
                "join_url": f"/meeting/{room_code}",
                "joinable": True,
            })
        else:
            start = _parse_iso(m.get("start_time"))
            end = _parse_iso(m.get("end_time"))
            joinable = bool(
                start
                and end
                and (start - JOIN_WINDOW_BEFORE_START) <= now <= end
            )
            enriched.append({**m, "joinable": joinable})

    return {"count": len(enriched), "results": enriched, "source": source}


def fetch_cards_summary(request):
    """
    cards 앱의 카드 목록 API(GET /api/v1/cards/)를 count만 필요한 최소 페이지로 호출.
    이미 api.md에 명세된 엔드포인트라 별도 신규 API 제안 불필요.
    """
    try:
        data = _call_internal_app("/api/v1/cards/?page=1&page_size=1", request)
        return {"count": data.get("count", 0), "source": "live"}
    except Exception:
        return {**mocks.MOCK_CARDS_SUMMARY, "source": "mock"}


def fetch_tracker_alert(request):
    """
    제안 스펙(신규): GET /api/v1/tracker/alerts/latest/ (JWT 인증)
    -> {has_alert, message, recurring_meeting_id}
    tracker 앱 담당자 확인 후 구현 필요. 그 전까지는 항상 목업.
    """
    try:
        data = _call_internal_app("/api/v1/tracker/alerts/latest/", request)
        return {**data, "source": "live"}
    except Exception:
        return {**mocks.MOCK_TRACKER_ALERT, "source": "mock"}


def fetch_latest_summary(request):
    """
    제안 스펙(신규, B 담당): GET /api/v1/summary/latest/ (JWT 인증)
    -> {available, meeting_title, action_item_count, created_at}
    summary 앱이 아직 없어 항상 목업으로 폴백됨.
    """
    try:
        raw = _call_external_service("SUMMARY_BASE_URL", "/api/v1/summary/latest/")
        return {**raw, "source": "live"}
    except UpstreamUnavailable:
        return {**mocks.MOCK_LATEST_SUMMARY, "source": "mock"}


def fetch_rehearsal_continue(request):
    """
    제안 스펙(신규): GET /api/v1/rehearsal/sessions/latest/ (JWT 인증)
    -> {available, session_id, persona_name, last_message_preview, updated_at}
    rehearsal 앱 담당자 확인 후 구현 필요. 그 전까지는 항상 목업.
    """
    try:
        data = _call_internal_app("/api/v1/rehearsal/sessions/latest/", request)
        return {**data, "source": "live"}
    except Exception:
        return {**mocks.MOCK_REHEARSAL_CONTINUE, "source": "mock"}


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
