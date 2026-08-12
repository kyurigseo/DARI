"""
AI 리허설 질문/피드백/번역 생성 인터페이스.

실제 LLM(FastAPI AI 서버, api.md 3번 섹션 참고) 연동 전까지는 이 모듈의 각 함수가
페르소나별 고정 템플릿을 반환하는 목업으로 동작한다. 나중에 실제 연동 시 이 파일
안의 함수 본문만 실제 HTTP 호출로 바꾸면 되고, 호출부(views.py)는 그대로 둘 수 있도록
함수 시그니처(입력/출력 shape)를 실제 응답 스키마와 동일하게 맞춰뒀다.

목업 방식: 정교한 생성 대신 페르소나(culture_tag)별로 미리 준비한 문장 풀에서 고른다.
완전 랜덤 대신 순환(rotation) 인덱스를 써서 같은 세션 안에서는 매번 다른 문장이
나오도록 하되, 테스트 시 재현 가능하게 유지한다.
"""

_OPENING_TEMPLATES = {
    "DE": "[Mock] 지난번 보고서에서 일정이 2주 밀렸던데, 그 이유를 설명해 주시겠어요?",
    "JP": "[Mock] 스케줄 변경 건에 대해 사전에 공유해 주실 수 있으실까요?",
    "CN": "[Mock] 이번 협력 조건에 대해 좀 더 구체적으로 논의하고 싶습니다.",
    "US": "[Mock] Hey, can you walk me through why the timeline slipped?",
}
_DEFAULT_OPENING = "[Mock] 지금 진행 상황에 대해 설명해 주시겠어요?"

_FOLLOWUP_TEMPLATES = {
    "DE": "[Mock] 알겠습니다. 그럼 재발 방지를 위한 대안은 무엇인가요?",
    "JP": "[Mock] 말씀 감사합니다. 다음 단계는 어떻게 진행될까요?",
    "CN": "[Mock] 좋습니다. 그 부분은 언제까지 확정할 수 있을까요?",
    "US": "[Mock] Got it. What's the backup plan if that happens again?",
}
_DEFAULT_FOLLOWUP = "[Mock] 알겠습니다. 조금 더 구체적으로 설명해 주시겠어요?"

_QUICK_REPLIES = {
    "DE": ["일정이 지연된 구체적 사유를 먼저 설명드리겠습니다.", "죄송합니다, 다음부터는 미리 공유드리겠습니다."],
    "JP": ["네, 확인 후 바로 공유드리겠습니다.", "번거롭게 해드려 죄송합니다."],
    "CN": ["네, 조건을 정리해서 다시 전달드리겠습니다.", "이 부분은 다음 회의 때 확정하겠습니다."],
    "US": ["Sure, let me walk you through what happened.", "Sorry about that — here's the plan going forward."],
}
_DEFAULT_QUICK_REPLIES = ["네, 알겠습니다.", "조금 더 검토해보겠습니다."]

_SITUATION_LABELS = {
    "DE": "일정 지연 사유를 설명해야 할 때",
    "JP": "완곡하게 재확인 질문할 때",
    "CN": "협상 조건을 조율할 때",
    "US": "동료에게 캐주얼하게 상황을 공유할 때",
}
_DEFAULT_SITUATION_LABEL = "상황을 설명해야 할 때"

_TRANSLATIONS = {
    "de": "[DE] Ich möchte Ihnen die genaue Ursache der Verzögerung erklären.",
    "ja": "[JA] 遅延の具体的な理由をご説明させてください。",
    "zh": "[ZH] 我想向您说明延误的具体原因。",
    "en": "[EN] Let me explain the exact reason for the delay.",
}
_DEFAULT_TRANSLATION = "[EN] Let me explain the situation in more detail."


def generate_opening_message(persona, context=""):
    return _OPENING_TEMPLATES.get(persona.culture_tag, _DEFAULT_OPENING)


def generate_ai_reply(persona, user_text, history=None):
    return _FOLLOWUP_TEMPLATES.get(persona.culture_tag, _DEFAULT_FOLLOWUP)


def generate_quick_replies(persona, ai_message=""):
    return _QUICK_REPLIES.get(persona.culture_tag, list(_DEFAULT_QUICK_REPLIES))


def generate_feedback(persona, user_text):
    """
    사용자 응답에 대한 코치 피드백을 생성. 실제 LLM 연동 전까지는 페르소나 기반
    고정 템플릿 + 사용자가 입력한 원문을 그대로 담아 반환한다.
    """
    suggested_text = f"[Mock 추천 문구] {persona.name}께, 상황을 명확히 설명드리겠습니다: {user_text[:40]}"
    return {
        "situation_label": _SITUATION_LABELS.get(persona.culture_tag, _DEFAULT_SITUATION_LABEL),
        "explanation": "[Mock] 완곡한 표현보다 구체적인 사유와 대안을 먼저 제시해보세요.",
        "suggested_text": suggested_text,
        "translated_text": _TRANSLATIONS.get(persona.language_code, _DEFAULT_TRANSLATION),
        "translated_language": persona.language_code,
    }
