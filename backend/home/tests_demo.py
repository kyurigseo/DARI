from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from cards.models import Card
from meetings.models import MeetingChatMessage, MeetingParticipant, MeetingSession
from tracker.models import AvailabilitySlot


class DemoModeGuardTests(SimpleTestCase):
    @override_settings(DARI_DEMO_MODE=False)
    def test_seed_refuses_to_run_without_demo_mode(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo_data", host_username="qwe")


@override_settings(DARI_DEMO_MODE=True)
class DemoModeIntegrationTests(APITestCase):
    def setUp(self):
        call_command("seed_demo_data", host_username="qwe", verbosity=0)
        self.host = get_user_model().objects.get(username="qwe")
        self.client = APIClient()
        access_token = RefreshToken.for_user(self.host).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

    def test_seed_is_idempotent(self):
        call_command("seed_demo_data", host_username="qwe", verbosity=0)
        meeting = MeetingSession.objects.get(room_code="demo-acme-negotiation")

        self.assertEqual(MeetingParticipant.objects.filter(meeting=meeting).count(), 4)
        self.assertEqual(MeetingChatMessage.objects.filter(meeting=meeting).count(), 3)
        self.assertEqual(Card.objects.filter(owner=self.host).count(), 3)
        self.assertEqual(AvailabilitySlot.objects.filter(participant=self.host).count(), 336)

    def test_demo_home_uses_seeded_meeting_room_code(self):
        response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        meeting = response.data["today_meetings"][0]
        self.assertEqual(meeting["title"], "Acme Corp 협상")
        self.assertEqual(meeting["room_code"], "demo-acme-negotiation")
        self.assertEqual(meeting["join_url"], "/meeting/demo-acme-negotiation")
        self.assertEqual(meeting["participant_count"], 4)

    def test_demo_rehearsal_cards_tracker_and_meeting_flow(self):
        summary_tabs = self.client.get("/api/meetings/summary-tabs/")
        self.assertEqual(summary_tabs.status_code, 200)
        self.assertEqual(len(summary_tabs.data), 3)
        self.assertTrue(all(tab["room_code"] for tab in summary_tabs.data))

        persona_response = self.client.get("/api/v1/rehearsal/personas/")
        self.assertEqual(persona_response.status_code, 200)

        session_response = self.client.post(
            "/api/v1/rehearsal/sessions/",
            {"persona_id": persona_response.data[0]["persona_id"], "context": "일정 협상"},
            format="json",
        )
        self.assertEqual(session_response.status_code, 201)
        self.assertTrue(session_response.data["opening_message"])

        message_response = self.client.post(
            f"/api/v1/rehearsal/sessions/{session_response.data['session_id']}/messages/",
            {"content": "예산 범위를 다시 검토하고 대안을 제시하겠습니다."},
            format="json",
        )
        self.assertEqual(message_response.status_code, 200)
        save_response = self.client.post(
            f"/api/v1/rehearsal/feedback/{message_response.data['feedback']['feedback_id']}/save-card/",
            {"category": "협상"},
            format="json",
        )
        self.assertEqual(save_response.status_code, 201, save_response.data)

        card_response = self.client.get("/api/v1/cards/")
        self.assertEqual(card_response.status_code, 200)
        self.assertEqual(card_response.data["count"], 4)

        slot_response = self.client.patch(
            "/api/v1/tracker/heatmap/me/",
            {"weekday": 0, "half_hour_index": 0, "status": "NEUTRAL"},
            format="json",
        )
        self.assertEqual(slot_response.status_code, 200)
        self.assertEqual(slot_response.data["status"], "NEUTRAL")

        prejoin_response = self.client.get("/api/meetings/demo-acme-negotiation/prejoin/")
        self.assertEqual(prejoin_response.status_code, 200)
        self.assertEqual(len(prejoin_response.data["participants"]), 4)
        self.assertEqual(len(prejoin_response.data["chat_history"]), 3)
        self.assertEqual(prejoin_response.data["title"], "Acme Corp 협상")

        end_response = self.client.post("/api/meetings/demo-acme-negotiation/end/")
        self.assertEqual(end_response.status_code, 200)

        report_response = self.client.get("/api/meetings/demo-acme-negotiation/report/")
        self.assertEqual(report_response.status_code, 200)
        self.assertNotEqual(report_response.data["ai_summary"], "아직 생성된 회의 요약이 없습니다.")
        self.assertGreaterEqual(len(report_response.data["action_items"]), 1)
