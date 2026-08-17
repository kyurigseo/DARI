import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.test import TestCase, override_settings

from rehearsal import ai_engine
from rehearsal.models import Persona, RehearsalMessage, RehearsalSession

User = get_user_model()


def _make_user(username):
    # accounts의 post_save 시그널(User -> UserProfile 자동 생성)은 이 리포지토리에서
    # accounts_userprofile 마이그레이션 상태에 따라 테스트 DB에서 실패할 수 있어,
    # rehearsal 테스트 범위 안에서만 잠시 꺼둔다(accounts 파일은 건드리지 않음).
    receivers = post_save.receivers
    post_save.receivers = []
    try:
        return User.objects.create_user(
            username=username, password="testpass123", email=f"{username}@example.com",
            country="KR", role="STAFF",
        )
    finally:
        post_save.receivers = receivers


def _fake_response(content):
    """groq.chat.completions.create()가 반환하는 ChatCompletion 모양을 흉내낸다:
    response.choices[0].message.content"""
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def _fake_client(create_impl):
    client = MagicMock()
    client.chat.completions.create.side_effect = create_impl
    return client


class AIEngineTextGenerationTests(TestCase):
    """opening/ai_reply — 실제 Groq 클라이언트는 mock으로 대체해 API를 호출하지 않는다."""

    def setUp(self):
        self.persona = Persona.objects.get(culture_tag="DE")

    @patch("rehearsal.ai_engine._get_client")
    def test_generate_opening_message_returns_text(self, mock_get_client):
        mock_get_client.return_value = _fake_client(
            lambda **kw: _fake_response("안녕하세요, 상황을 설명해 주시겠어요?")
        )
        result = ai_engine.generate_opening_message(self.persona, context="일정 지연")
        self.assertEqual(result, "안녕하세요, 상황을 설명해 주시겠어요?")

    @patch("rehearsal.ai_engine._get_client")
    def test_generate_ai_reply_includes_history_in_messages(self, mock_get_client):
        captured = {}

        def impl(**kwargs):
            captured.update(kwargs)
            return _fake_response("알겠습니다.")

        mock_get_client.return_value = _fake_client(impl)

        user = _make_user("histuser")
        session = RehearsalSession.objects.create(user=user, persona=self.persona, context="")
        RehearsalMessage.objects.create(session=session, role=RehearsalMessage.Role.AI, content="첫 질문입니다.")
        history = list(session.messages.all())

        result = ai_engine.generate_ai_reply(self.persona, "제 답변입니다.", history=history)

        self.assertEqual(result, "알겠습니다.")
        messages = captured["messages"]
        self.assertEqual(messages[0]["role"], "system")
        # AI 역할은 OpenAI 호환 스펙의 "assistant"로 매핑돼야 한다.
        self.assertEqual(messages[1], {"role": "assistant", "content": "첫 질문입니다."})
        self.assertEqual(messages[-1], {"role": "user", "content": "제 답변입니다."})

    @patch("rehearsal.ai_engine._get_client")
    @override_settings(DARI_DEMO_MODE=False)
    def test_api_error_becomes_ai_engine_unavailable(self, mock_get_client):
        def impl(**kw):
            raise TimeoutError("simulated timeout")

        mock_get_client.return_value = _fake_client(impl)
        with self.assertRaises(ai_engine.AIEngineUnavailable) as ctx:
            ai_engine.generate_opening_message(self.persona)
        self.assertEqual(ctx.exception.status_code, 502)

    @patch("rehearsal.ai_engine._get_client")
    @override_settings(DARI_DEMO_MODE=True, GROQ_API_KEY="invalid-demo-key")
    def test_api_error_uses_fallback_in_demo_mode(self, mock_get_client):
        mock_get_client.return_value = _fake_client(
            lambda **kw: (_ for _ in ()).throw(TimeoutError("simulated timeout"))
        )

        result = ai_engine.generate_opening_message(self.persona)

        self.assertIn("구체적인 근거", result)

    @override_settings(GROQ_API_KEY="")
    def test_missing_api_key_raises_ai_engine_unavailable(self):
        ai_engine._client = None
        try:
            with self.assertRaises(ai_engine.AIEngineUnavailable):
                ai_engine._get_client()
        finally:
            ai_engine._client = None


class AIEngineJsonGenerationTests(TestCase):
    """quick_replies/feedback — 구조화된 JSON 응답 파싱과 검증."""

    def setUp(self):
        self.persona = Persona.objects.get(culture_tag="DE")

    @patch("rehearsal.ai_engine._get_client")
    def test_generate_quick_replies_parses_json_object(self, mock_get_client):
        mock_get_client.return_value = _fake_client(
            lambda **kw: _fake_response(json.dumps({"replies": ["네, 알겠습니다.", "확인 후 다시 말씀드릴게요."]}))
        )
        result = ai_engine.generate_quick_replies(self.persona, ai_message="질문입니다")
        self.assertEqual(result, ["네, 알겠습니다.", "확인 후 다시 말씀드릴게요."])

    @patch("rehearsal.ai_engine._get_client")
    def test_generate_quick_replies_raises_on_malformed_json(self, mock_get_client):
        mock_get_client.return_value = _fake_client(lambda **kw: _fake_response("이건 JSON이 아님"))
        with self.assertRaises(ai_engine.AIEngineUnavailable):
            ai_engine.generate_quick_replies(self.persona)

    @patch("rehearsal.ai_engine._get_client")
    def test_generate_feedback_parses_json_object(self, mock_get_client):
        payload = {
            "situation_label": "일정 지연 사유를 설명해야 할 때",
            "explanation": "구체적인 대안을 먼저 제시해보세요.",
            "suggested_text": "일정이 늦어진 이유는 다음과 같습니다.",
            "translated_text": "Der Grund fuer die Verzoegerung ist folgender.",
        }
        mock_get_client.return_value = _fake_client(lambda **kw: _fake_response(json.dumps(payload)))
        result = ai_engine.generate_feedback(self.persona, "일정이 늦어졌습니다.")
        self.assertEqual(result["situation_label"], payload["situation_label"])
        self.assertEqual(result["translated_text"], payload["translated_text"])
        self.assertEqual(result["translated_language"], "de")

    @patch("rehearsal.ai_engine._get_client")
    def test_generate_feedback_raises_on_missing_field(self, mock_get_client):
        incomplete = {"situation_label": "라벨", "explanation": "설명"}
        mock_get_client.return_value = _fake_client(lambda **kw: _fake_response(json.dumps(incomplete)))
        with self.assertRaises(ai_engine.AIEngineUnavailable):
            ai_engine.generate_feedback(self.persona, "테스트")


class PersonaSystemPromptTests(TestCase):
    """4개 페르소나가 실제로 서로 다른 system prompt를 쓰는지 확인."""

    def test_all_four_personas_get_distinct_prompts(self):
        prompts = {
            tag: ai_engine._persona_system_prompt(Persona.objects.get(culture_tag=tag))
            for tag in ("DE", "JP", "CN", "US")
        }
        self.assertEqual(len(set(prompts.values())), 4)

    @patch("rehearsal.ai_engine._get_client")
    def test_system_message_sent_to_groq_differs_per_persona(self, mock_get_client):
        captured = []

        def impl(**kwargs):
            captured.append(kwargs["messages"][0]["content"])
            return _fake_response("응답")

        mock_get_client.return_value = _fake_client(impl)

        for tag in ("DE", "JP", "CN", "US"):
            ai_engine.generate_opening_message(Persona.objects.get(culture_tag=tag))

        self.assertEqual(len(set(captured)), 4)


@unittest.skipUnless(
    os.environ.get("GROQ_API_KEY"), "GROQ_API_KEY가 없어 실제 Groq 연동 테스트를 건너뜁니다."
)
class GroqLiveIntegrationTests(TestCase):
    """실제 Groq API를 호출하는 테스트. GROQ_API_KEY가 설정된 환경에서만 실행된다."""

    def setUp(self):
        ai_engine._client = None

    def tearDown(self):
        ai_engine._client = None

    def test_generate_opening_message_hits_real_api(self):
        persona = Persona.objects.get(culture_tag="DE")
        result = ai_engine.generate_opening_message(persona, context="분기 보고서 일정 지연")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result.strip()), 0)

    def test_generate_feedback_hits_real_api(self):
        persona = Persona.objects.get(culture_tag="JP")
        result = ai_engine.generate_feedback(persona, "죄송합니다, 다음부터는 미리 말씀드리겠습니다.")
        for key in ("situation_label", "explanation", "suggested_text", "translated_text", "translated_language"):
            self.assertIn(key, result)
        self.assertEqual(result["translated_language"], "ja")
