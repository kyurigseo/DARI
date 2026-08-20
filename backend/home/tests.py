from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from meetings.models import MeetingParticipant, MeetingSession


class HomeDashboardLiveMeetingsTests(APITestCase):
    """DARI_DEMO_MODE가 아닌 일반 유저 경로에서 today_meetings가 실제 meetings DB를
    조회하는지 확인한다 (fetch_today_meetings가 MEETINGS_BASE_URL 미설정으로 항상
    mock 폴백되던 회귀를 방지)."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="pw12345!")
        self.meeting = MeetingSession.objects.create(
            room_code="room-live-1", title="실서비스 회의", host=self.user, status="WAITING"
        )
        MeetingParticipant.objects.create(meeting=self.meeting, user=self.user, is_host=True, is_active=True)

        access_token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

    def test_today_meetings_uses_real_meeting_row_not_mock(self):
        response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        meetings = response.data["today_meetings"]
        self.assertEqual(len(meetings), 1)
        meeting = meetings[0]
        self.assertEqual(meeting["room_code"], "room-live-1")
        self.assertEqual(meeting["title"], "실서비스 회의")
        self.assertEqual(meeting["participant_count"], 1)
        self.assertEqual(meeting["join_url"], "/meeting/room-live-1")
        self.assertNotIn("(mock)", meeting["title"])

    def test_today_meetings_uses_scheduled_start_time_when_set(self):
        scheduled = timezone.now() + timedelta(hours=3)
        self.meeting.scheduled_start_time = scheduled
        self.meeting.save(update_fields=["scheduled_start_time"])

        response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        meeting = response.data["today_meetings"][0]
        # DRF는 UTC 오프셋을 "+00:00" 대신 "Z"로 렌더링하므로 문자열이 아닌 파싱된
        # datetime으로 비교한다(같은 시각의 다른 표기일 뿐, 버그 아님).
        returned_start = datetime.fromisoformat(meeting["start_time"])
        self.assertEqual(returned_start, scheduled)
        self.assertNotEqual(returned_start, self.meeting.created_at)

    def test_today_meetings_falls_back_to_created_at_without_scheduled_start_time(self):
        self.assertIsNone(self.meeting.scheduled_start_time)

        response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        meeting = response.data["today_meetings"][0]
        returned_start = datetime.fromisoformat(meeting["start_time"])
        self.assertEqual(returned_start, self.meeting.created_at)

    def test_ended_meeting_is_excluded(self):
        self.meeting.status = "ENDED"
        self.meeting.save(update_fields=["status"])

        response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["today_meeting_count"], 0)
        self.assertEqual(response.data["today_meetings"], [])
