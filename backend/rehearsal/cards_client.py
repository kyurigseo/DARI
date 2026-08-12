"""
cards 앱과의 유일한 연동 지점. cards의 모델/코드는 절대 import하지 않고,
cards가 노출하는 POST /api/v1/cards/ 계약만 호출한다.

cards는 rehearsal과 같은 Django 프로세스에서 도는 A 담당 앱이라, home 앱에서 쓴 것과
동일하게 실제 소켓 통신 없이 django.test.Client로 URL 계약만 태운다
(home/clients.py에서 검증된 SERVER_NAME 고정 패턴 재사용).

카드 저장은 사용자가 명시적으로 누르는 쓰기 액션이므로, cards API가 아직 없거나
실패하면 "저장된 것처럼" 목업 성공을 반환하지 않고 예외를 그대로 올려 호출부(views.py)가
502로 응답하게 한다 — 실제로 존재하지 않는 카드를 저장됐다고 속이지 않기 위함.
"""

import json

from django.test import Client as DjangoTestClient

_client = DjangoTestClient()


class CardsUnavailable(Exception):
    pass


def create_card(request, *, original_text, suggested_text, translated_text,
                 translated_language, situation_label, partner_tag,
                 category, explanation):
    """
    제안 스펙 (2026-08-13 확정): POST /api/v1/cards/
    body: {original_text, suggested_text, translated_text, translated_language,
           situation_label, partner_tag, category, explanation}
    -> 201 {card_id, ...}
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION")
    extra = {"HTTP_AUTHORIZATION": auth_header} if auth_header else {}

    payload = {
        "original_text": original_text,
        "suggested_text": suggested_text,
        "translated_text": translated_text,
        "translated_language": translated_language,
        "situation_label": situation_label,
        "partner_tag": partner_tag,
        "category": category or "미분류",
        "explanation": explanation,
    }

    response = _client.post(
        "/api/v1/cards/",
        data=json.dumps(payload),
        content_type="application/json",
        SERVER_NAME="127.0.0.1",
        **extra,
    )
    if response.status_code != 201:
        raise CardsUnavailable(f"POST /api/v1/cards/ -> {response.status_code}")

    body = json.loads(response.content)
    card_id = body.get("card_id") or body.get("id")
    if not card_id:
        raise CardsUnavailable("cards response missing card_id")
    return card_id
