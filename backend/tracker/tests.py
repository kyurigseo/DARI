from datetime import datetime, timedelta, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from . import services
from .models import AvailabilitySlot, ParticipationRecord

User = get_user_model()


def _make_user(username, **extra):
    # accounts 앱의 post_save 시그널(User -> UserProfile 자동 생성)은 이 리포지토리 현재
    # 상태에서 accounts_userprofile 마이그레이션이 없어 테스트 DB에서 실패한다. accounts 파일은
    # 건드리지 않기로 되어 있으므로, tracker 테스트 범위 안에서만 해당 시그널을 잠시 끈다.
    receivers = post_save.receivers
    post_save.receivers = []
    try:
        return User.objects.create_user(
            username=username,
            password="testpass123",
            email=f"{username}@example.com",
            country="KR",
            role="STAFF",
            **extra,
        )
    finally:
        post_save.receivers = receivers


def _auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


class BucketClassificationTests(TestCase):
    def test_dawn_bucket(self):
        # 04:00 KST -> DAWN
        dt = datetime(2026, 8, 15, 19, 0, tzinfo=dt_timezone.utc)  # 2026-08-16 04:00 KST
        self.assertEqual(services.classify_bucket(dt, "Asia/Seoul"), services.DAWN)

    def test_daytime_bucket(self):
        dt = datetime(2026, 8, 15, 3, 0, tzinfo=dt_timezone.utc)  # 12:00 KST
        self.assertEqual(services.classify_bucket(dt, "Asia/Seoul"), services.DAYTIME)

    def test_evening_bucket(self):
        dt = datetime(2026, 8, 15, 11, 0, tzinfo=dt_timezone.utc)  # 20:00 KST
        self.assertEqual(services.classify_bucket(dt, "Asia/Seoul"), services.EVENING)


class BiasAlertTests(TestCase):
    def setUp(self):
        self.user = _make_user("alice")

    def _create_dawn_record(self, days_ago):
        meeting_time = datetime(2026, 8, 15, 20, 0, tzinfo=dt_timezone.utc) - timedelta(days=days_ago)
        ParticipationRecord.objects.create(
            participant=self.user,
            meeting_time_utc=meeting_time,
            local_timezone="Asia/Seoul",
            external_meeting_id="standup",
        )

    def test_no_alert_with_too_few_records(self):
        for i in range(3):
            self._create_dawn_record(i)
        result = services.detect_bias_alert(self.user)
        self.assertFalse(result["has_alert"])

    def test_alert_when_dawn_dominant(self):
        for i in range(5):
            self._create_dawn_record(i)
        result = services.detect_bias_alert(self.user)
        self.assertTrue(result["has_alert"])
        self.assertIn("새벽", result["message"])
        self.assertEqual(result["recurring_meeting_id"], "standup")

    def test_no_alert_when_daytime_dominant(self):
        for i in range(6):
            meeting_time = datetime(2026, 8, 15, 3, 0, tzinfo=dt_timezone.utc) - timedelta(days=i)
            ParticipationRecord.objects.create(
                participant=self.user, meeting_time_utc=meeting_time, local_timezone="Asia/Seoul"
            )
        result = services.detect_bias_alert(self.user)
        self.assertFalse(result["has_alert"])


class RecommendationTests(TestCase):
    def setUp(self):
        self.alice = _make_user("alice")
        self.bob = _make_user("bob")

    def test_prefers_slot_with_no_uncomfortable(self):
        AvailabilitySlot.objects.create(
            participant=self.alice, weekday=1, half_hour_index=20, status=AvailabilitySlot.UNCOMFORTABLE
        )
        AvailabilitySlot.objects.create(
            participant=self.bob, weekday=1, half_hour_index=20, status=AvailabilitySlot.COMFORTABLE
        )
        AvailabilitySlot.objects.create(
            participant=self.alice, weekday=2, half_hour_index=18, status=AvailabilitySlot.COMFORTABLE
        )
        AvailabilitySlot.objects.create(
            participant=self.bob, weekday=2, half_hour_index=18, status=AvailabilitySlot.COMFORTABLE
        )

        best = services.recommend_slot([str(self.alice.id), str(self.bob.id)])
        self.assertEqual((best["weekday"], best["half_hour_index"]), (2, 18))
        self.assertEqual(best["uncomfortable_count"], 0)


class HeatmapPermissionTests(TestCase):
    def setUp(self):
        self.alice = _make_user("alice")
        self.bob = _make_user("bob")

    def test_cannot_write_other_users_slot(self):
        client = _auth_client(self.alice)
        response = client.patch(
            reverse("tracker-heatmap-me"), {"weekday": 0, "half_hour_index": 10, "status": "COMFORTABLE"}
        )
        self.assertEqual(response.status_code, 200)
        slot = AvailabilitySlot.objects.get(weekday=0, half_hour_index=10)
        self.assertEqual(slot.participant_id, self.alice.id)
        self.assertNotEqual(slot.participant_id, self.bob.id)


class AlertsLatestEndpointTests(TestCase):
    def test_matches_home_contract_shape(self):
        user = _make_user("carol")
        client = _auth_client(user)
        response = client.get(reverse("tracker-alerts-latest"))
        self.assertEqual(response.status_code, 200)
        for key in ("has_alert", "message", "recurring_meeting_id"):
            self.assertIn(key, response.json())


class ParticipationIngestPermissionTests(TestCase):
    def test_rejects_without_internal_token(self):
        client = APIClient()
        response = client.post(
            reverse("tracker-participation-ingest"),
            {
                "meeting_time_utc": "2026-08-15T09:00:00Z",
                "participants": [],
            },
            format="json",
        )
        # JWTAuthentication만 등록돼 있고 "Internal ..." 스킴은 인식하지 못하므로
        # successful_authenticator가 없는 상태로 남아 DRF가 401(NotAuthenticated)로 처리한다.
        self.assertEqual(response.status_code, 401)

    def test_rejects_with_wrong_internal_token(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Internal wrong-token")
        response = client.post(
            reverse("tracker-participation-ingest"),
            {"meeting_time_utc": "2026-08-15T09:00:00Z", "participants": []},
            format="json",
        )
        # JWTAuthentication은 "Internal ..." 스킴을 아예 인식하지 못해 successful_authenticator가
        # 여전히 없는 상태로 남으므로, 값이 틀려도 DRF는 401로 응답한다(403이 되려면 유효한 인증
        # 수단으로 "인증은 됐지만 권한이 없는" 상태여야 함). IsInternalService는 애초에 별도
        # 인증 수단이 아니라 permission 체크이므로 이 401은 의도된 동작이다.
        self.assertEqual(response.status_code, 401)

    def test_accepts_with_internal_token(self):
        from django.conf import settings

        user = _make_user("dave")
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Internal {settings.INTERNAL_SERVICE_TOKEN}")
        response = client.post(
            reverse("tracker-participation-ingest"),
            {
                "external_meeting_id": "room-1",
                "meeting_title": "Weekly Sync",
                "meeting_time_utc": "2026-08-15T09:00:00Z",
                "participants": [
                    {
                        "user_id": str(user.id),
                        "local_timezone": "Asia/Seoul",
                        "local_region": "Seoul, KR",
                        "speaking_duration_seconds": 300,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ParticipationRecord.objects.filter(participant=user).count(), 1)


class MeetingConfirmIntegrationTests(TestCase):
    """meetings.CreateMeetingView / ParticipantManageView를 실제로 호출하는지 확인하는
    end-to-end 테스트. meetings 모델은 결과 검증에만 읽기로 사용하고, 호출 자체는
    tracker.meetings_client가 노출된 URL 계약으로만 수행한다."""

    # tracker.meetings_client는 home/clients.py와 동일하게 내부 호출에 SERVER_NAME="127.0.0.1"을
    # 쓴다(DEBUG=True + ALLOWED_HOSTS=[]일 때 Django가 127.0.0.1을 자동 허용하는 것에 기대는
    # 패턴). 다만 `manage.py test`는 테스트 환경에서 ALLOWED_HOSTS에 "testserver"를 추가해
    # 버려서(더 이상 빈 리스트가 아니게 됨) 그 자동 허용 폴백이 꺼진다 — 실제 개발 서버 동작과
    # 무관한 테스트 러너 한정 현상이라 여기서만 127.0.0.1을 명시적으로 허용한다.
    @override_settings(ALLOWED_HOSTS=["testserver", "127.0.0.1"])
    def test_confirm_creates_meetings_room_and_invites_participant(self):
        from meetings.models import MeetingParticipant, MeetingSession

        alice = _make_user("alice")
        bob = _make_user("bob")
        client = _auth_client(alice)

        response = client.post(
            reverse("tracker-meeting-confirm"),
            {
                "title": "Q3 예산안 협상",
                "weekday": 2,
                "half_hour_index": 18,
                "participant_ids": [str(bob.id)],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["meetings_sync_status"], "SYNCED")
        self.assertTrue(body["room_code"])

        meeting = MeetingSession.objects.get(room_code=body["room_code"])
        self.assertEqual(meeting.host, alice)
        self.assertTrue(MeetingParticipant.objects.filter(meeting=meeting, user=bob).exists())
