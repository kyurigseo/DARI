"""
AI 리허설 질문/피드백/번역 생성 인터페이스 — Groq API 연동.

Gemini가 프로젝트 권한 문제(403 PERMISSION_DENIED)로 막혀서 Groq(OpenAI 호환 chat
completions API)로 교체했다. 호출부(rehearsal/views.py)와의 계약을 지키기 위해 함수
시그니처(입력/출력 shape)는 그대로 유지하고, 본문만 Groq 호출로 교체했다.

에러 처리: 실패 시 목업으로 조용히 폴백하지 않고 AIEngineUnavailable을 던진다. 이 예외는
DRF의 APIException을 상속해 status_code=502를 갖고 있어서, views.py가 별도로
try/except 하지 않아도 DRF의 기본 예외 처리기가 자동으로 502 JSON 응답을 만들어준다.
"""

import json
import logging

import groq
from django.conf import settings
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)

GROQ_MODEL_NAME = getattr(settings, "GROQ_MODEL_NAME", "openai/gpt-oss-120b")
GROQ_TIMEOUT_SECONDS = getattr(settings, "GROQ_TIMEOUT_SECONDS", 12)

LANGUAGE_NAMES = {"de": "독일어", "ja": "일본어", "zh": "중국어", "en": "영어"}

DEMO_OPENINGS = {
    "DE": "이번 일정 지연의 원인과 재발 방지 대책을 구체적으로 설명해주시겠어요?",
    "JP": "이번 제안에 관해 사전에 조금 더 공유해주실 수 있을까요?",
    "CN": "양쪽 모두에게 도움이 되는 조건을 함께 찾아보면 어떨까요?",
    "US": "좋아요, 지금 가장 먼저 해결해야 할 이슈부터 이야기해볼까요?",
}


class AIEngineUnavailable(APIException):
    """Groq 호출 실패(키 없음/타임아웃/rate limit/응답 파싱 실패 등)를 나타내는 예외.
    DRF APIException을 상속했으므로 views.py가 잡지 않아도 502로 응답된다."""

    status_code = 502
    default_detail = "AI 리허설 서비스에 일시적으로 연결할 수 없습니다. 잠시 후 다시 시도해주세요."
    default_code = "ai_engine_unavailable"


# ---------------------------------------------------------------------------
# 페르소나별 system prompt — Gemini 연동 때 만든 내용을 그대로 재사용(수정 없음)
# ---------------------------------------------------------------------------
PERSONA_SYSTEM_PROMPTS = {
    "DE": (
        "당신은 '{name}'입니다 — 직설적이고 사실 기반의 커뮤니케이션을 선호하는 독일 팀장입니다.\n"
        "- 완곡한 표현보다 명확한 이유와 구체적인 대안을 요구합니다.\n"
        "- 일정 지연, 책임 소재, 재발 방지 대책 같은 주제에 특히 예민합니다.\n"
        "- 상대가 애매하게 답하면 더 구체적으로 캐묻습니다.\n"
        "- 무례하지 않지만 사무적이고 단도직입적인 어조를 씁니다."
    ),
    "JP": (
        "당신은 '{name}'입니다 — 완곡하고 예의를 중시하는 일본 클라이언트입니다.\n"
        "- 직접적인 지적보다 돌려 말하는 질문으로 우회적으로 확인합니다.\n"
        "- 사전 공유, 절차, 상대에 대한 배려를 중요하게 여깁니다.\n"
        "- 상대의 체면을 지켜주면서도 필요한 확인은 끝까지 합니다.\n"
        "- 항상 정중하고 부드러운 존댓말 어조를 씁니다."
    ),
    "CN": (
        "당신은 '{name}'입니다 — 관계와 협상의 유연성을 중시하는 중국 비즈니스 파트너입니다.\n"
        "- 조건과 일정을 유연하게 조율하려 하며, 관계를 해치지 않는 선에서 실리를 챙깁니다.\n"
        "- 협상 여지를 남기는 화법을 쓰고, 상대 제안에 대한 대안을 자주 제시합니다.\n"
        "- 우호적이지만 은근히 자신에게 유리한 조건을 이끌어내려 합니다."
    ),
    "US": (
        "당신은 '{name}'입니다 — 캐주얼하고 직접적인 커뮤니케이션을 선호하는 미국 동료입니다.\n"
        "- 격식보다 친근함을 중시하고 요점을 바로 이야기합니다.\n"
        "- 편하고 친근한 구어체를 쓰되 무례하지 않게 합니다.\n"
        "- 문제가 생기면 원인 추궁보다 다음 액션(대안/플랜B)에 먼저 관심을 둡니다."
    ),
}
_DEFAULT_SYSTEM_PROMPT = "당신은 '{name}'입니다. 비즈니스 상황극 리허설 상대 역할을 맡아 자연스럽게 대화하세요."

_CHAT_STYLE_SUFFIX = (
    "\n\n반드시 한국어로, 실제 채팅 메신저에서 보낼 법한 1~2문장으로만 답하세요. "
    "행동 지문(예: '*웃으며*')이나 부가 설명 없이 대사만 출력하세요."
)


def _persona_system_prompt(persona):
    template = PERSONA_SYSTEM_PROMPTS.get(persona.culture_tag, _DEFAULT_SYSTEM_PROMPT)
    return template.format(name=persona.name) + _CHAT_STYLE_SUFFIX


# ---------------------------------------------------------------------------
# Groq 클라이언트 / 저수준 호출 helper
# ---------------------------------------------------------------------------

_client = None

# Groq(OpenAI 호환) SDK에서 네트워크/응답 오류를 나타내는 예외들. RateLimitError는 사실
# APIStatusError의 서브클래스라 두 번째 것만 잡아도 되지만, 무엇을 명시적으로 다루는지
# 드러내기 위해 셋 다 나열한다.
_GROQ_ERRORS = (groq.APIConnectionError, groq.RateLimitError, groq.APIStatusError)


def _get_client():
    global _client
    if _client is not None:
        return _client

    api_key = getattr(settings, "GROQ_API_KEY", "")
    if not api_key:
        raise AIEngineUnavailable("GROQ_API_KEY가 설정되지 않았습니다.")

    _client = groq.Groq(api_key=api_key, timeout=GROQ_TIMEOUT_SECONDS)
    return _client


def _demo_enabled():
    return bool(getattr(settings, "DARI_DEMO_MODE", False))


def _demo_completion(messages, as_json):
    """Return deterministic output only after a failed Groq call in demo mode."""
    prompt = "\n".join(message.get("content", "") for message in messages)
    if as_json and '"replies"' in prompt:
        return json.dumps({
            "replies": [
                "핵심 근거부터 설명드리겠습니다.",
                "구체적인 대안을 함께 제안드리겠습니다.",
            ]
        }, ensure_ascii=False)
    if as_json:
        return json.dumps({
            "situation_label": "근거와 대안을 명확히 전달해야 하는 상황",
            "explanation": "요점을 먼저 말하고 구체적인 근거와 다음 행동을 덧붙이면 더 설득력 있어요.",
            "suggested_text": "핵심 이유를 먼저 설명드린 뒤 실행 가능한 대안을 제안하겠습니다.",
            "translated_text": "I'd like to explain the key reasons first, then propose an actionable alternative.",
        }, ensure_ascii=False)
    return "좋습니다. 그 입장을 뒷받침할 구체적인 근거와 실행 가능한 대안을 말씀해주시겠어요?"


def _chat_completion(system_prompt, messages, *, temperature, as_json):
    client = _get_client()
    full_messages = [{"role": "system", "content": system_prompt}, *messages]

    kwargs = {"model": GROQ_MODEL_NAME, "messages": full_messages, "temperature": temperature}
    if as_json:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = client.chat.completions.create(**kwargs)
    except AIEngineUnavailable:
        raise
    except _GROQ_ERRORS as exc:
        if _demo_enabled():
            logger.warning("Groq failed; using deterministic demo fallback: %s", exc)
            return _demo_completion(messages, as_json)
        logger.warning("Groq chat.completions 실패: %s", exc)
        raise AIEngineUnavailable(f"AI 응답 생성에 실패했습니다: {exc}") from exc
    except Exception as exc:  # SDK 내부 오류 등 위에서 못 잡는 경우까지 전부 동일하게 취급
        if _demo_enabled():
            logger.warning("Groq failed; using deterministic demo fallback: %s", exc)
            return _demo_completion(messages, as_json)
        logger.warning("Groq chat.completions 실패(미분류): %s", exc)
        raise AIEngineUnavailable(f"AI 응답 생성에 실패했습니다: {exc}") from exc

    choices = getattr(response, "choices", None) or []
    content = (choices[0].message.content if choices else None) or ""
    content = content.strip()
    if not content:
        if _demo_enabled():
            return _demo_completion(messages, as_json)
        raise AIEngineUnavailable("AI 응답이 비어 있습니다.")
    return content


def _generate_text(system_prompt, messages, *, temperature=0.8):
    return _chat_completion(system_prompt, messages, temperature=temperature, as_json=False)


def _generate_json(system_prompt, messages, *, temperature=0.7):
    raw = _chat_completion(system_prompt, messages, temperature=temperature, as_json=True)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise AIEngineUnavailable("AI 응답을 해석할 수 없습니다.") from exc


def _build_conversation_messages(history, user_text):
    """RehearsalMessage(.role in {AI, USER}, .content)들을 OpenAI 호환
    messages=[{"role": "user"/"assistant", "content": ...}, ...] 형식으로 변환하고,
    이번 턴의 새 사용자 발화를 마지막에 덧붙인다. (system 메시지는 여기서 넣지 않고
    _chat_completion이 공통으로 맨 앞에 붙인다.)"""
    messages = []
    for message in history or []:
        role = "assistant" if getattr(message, "role", None) == "AI" else "user"
        messages.append({"role": role, "content": message.content})
    messages.append({"role": "user", "content": user_text})
    return messages


# ---------------------------------------------------------------------------
# 공개 API — 함수 시그니처는 그대로 유지
# ---------------------------------------------------------------------------


def generate_opening_message(persona, context=""):
    if _demo_enabled() and not getattr(settings, "GROQ_API_KEY", ""):
        return DEMO_OPENINGS.get(persona.culture_tag, "오늘 연습하고 싶은 업무 상황을 말씀해주세요.")
    system_prompt = _persona_system_prompt(persona)
    situation = context.strip() or "일반적인 업무 상황"
    prompt = (
        f"리허설을 시작합니다. 사용자가 연습하려는 상황: {situation}\n"
        "이 상황에 맞춰 당신의 역할(페르소나)로서 사용자에게 먼저 건넬 첫 질문 또는 발화를 작성하세요."
    )
    return _generate_text(system_prompt, [{"role": "user", "content": prompt}])


def generate_ai_reply(persona, user_text, history=None):
    if _demo_enabled() and not getattr(settings, "GROQ_API_KEY", ""):
        return f"좋습니다. ‘{user_text[:40]}’라는 입장을 뒷받침할 구체적인 근거도 알려주시겠어요?"
    system_prompt = _persona_system_prompt(persona)
    messages = _build_conversation_messages(history, user_text)
    return _generate_text(system_prompt, messages)


def generate_quick_replies(persona, ai_message=""):
    if _demo_enabled() and not getattr(settings, "GROQ_API_KEY", ""):
        return ["핵심 근거부터 설명드리겠습니다.", "구체적인 대안을 함께 제안드리겠습니다."]
    system_prompt = _persona_system_prompt(persona)
    prompt = (
        f'당신(페르소나)이 방금 이렇게 말했습니다: "{ai_message}"\n'
        "리허설 중인 사용자가 다음 응답으로 바로 골라 쓸 수 있는 짧은 한국어 답변 예시를 2개 제안하세요.\n"
        '정확히 이 JSON 형식으로만 응답하세요: {"replies": ["답변1", "답변2"]}'
    )
    result = _generate_json(system_prompt, [{"role": "user", "content": prompt}], temperature=0.9)

    replies = result.get("replies") if isinstance(result, dict) else None
    if not isinstance(replies, list) or not replies or not all(
        isinstance(x, str) and x.strip() for x in replies
    ):
        raise AIEngineUnavailable("퀵리플라이 응답 형식이 올바르지 않습니다.")
    return replies[:2]


def generate_feedback(persona, user_text):
    """
    사용자 응답에 대한 코치 피드백을 생성한다.
    """
    if _demo_enabled() and not getattr(settings, "GROQ_API_KEY", ""):
        translations = {
            "de": "Ich möchte zunächst die wichtigsten Gründe erläutern und anschließend eine konkrete Alternative vorschlagen.",
            "ja": "まず主な理由をご説明し、その後で具体的な代案をご提案します。",
            "zh": "我想先说明主要原因，然后提出一个具体的替代方案。",
            "en": "I'd like to explain the main reasons first, then propose a concrete alternative.",
        }
        return {
            "situation_label": "근거와 대안을 명확히 전달해야 할 때",
            "explanation": "요점을 먼저 말하고 구체적인 근거와 다음 행동을 덧붙이면 더 설득력 있어요.",
            "suggested_text": "핵심 이유를 먼저 설명드린 뒤, 실행 가능한 대안을 제안하겠습니다.",
            "translated_text": translations.get(persona.language_code, translations["en"]),
            "translated_language": persona.language_code,
        }

    system_prompt = _persona_system_prompt(persona)
    target_language = LANGUAGE_NAMES.get(persona.language_code, persona.language_code)
    prompt = (
        "리허설 중인 사용자가 방금 이렇게 답했습니다:\n"
        f'"{user_text}"\n\n'
        "이 응답에 대한 코칭 피드백을 아래 항목에 맞춰 생성하세요.\n"
        "- situation_label: 지금 상황을 한국어로 짧게 요약한 라벨 (예: '일정 지연 사유를 설명해야 할 때')\n"
        "- explanation: 어떤 점을 개선하면 좋을지 한국어로 1~2문장 코멘트\n"
        "- suggested_text: 지금 상황에 더 적합한 한국어 응답 예시 문장\n"
        f"- translated_text: suggested_text를 {target_language}로 번역한 문장\n\n"
        "정확히 이 JSON 형식으로만 응답하세요: "
        '{"situation_label": "...", "explanation": "...", "suggested_text": "...", "translated_text": "..."}'
    )
    result = _generate_json(system_prompt, [{"role": "user", "content": prompt}], temperature=0.6)

    required_keys = ("situation_label", "explanation", "suggested_text", "translated_text")
    if not isinstance(result, dict) or not all(
        isinstance(result.get(k), str) and result.get(k).strip() for k in required_keys
    ):
        raise AIEngineUnavailable("피드백 응답 형식이 올바르지 않습니다.")

    return {
        "situation_label": result["situation_label"],
        "explanation": result["explanation"],
        "suggested_text": result["suggested_text"],
        "translated_text": result["translated_text"],
        "translated_language": persona.language_code,
    }
