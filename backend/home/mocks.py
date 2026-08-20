"""
홈 대시보드가 의존하는 외부 API가 아직 없거나 응답에 실패했을 때 쓰는 목업 데이터.
각 앱이 실제 엔드포인트를 구현하면 home/clients.py의 해당 fetch 함수만 라이브 호출로
전환되고, 이 파일의 상수는 실패 시 폴백(fallback)으로만 남는다.
"""

MOCK_TODAY_MEETINGS = [
    {
        "meeting_id": "00000000-0000-0000-0000-000000000001",
        "title": "(mock) Q3 예산안 협상",
        "start_time": "2026-08-13T10:00:00+09:00",
        "end_time": "2026-08-13T11:00:00+09:00",
        "participant_count": 5,
        "join_url": None,
    },
    {
        "meeting_id": "00000000-0000-0000-0000-000000000002",
        "title": "(mock) 독일 팀 위클리 싱크",
        "start_time": "2026-08-13T18:00:00+09:00",
        "end_time": "2026-08-13T18:30:00+09:00",
        "participant_count": 4,
        "join_url": None,
    },
]

MOCK_CARDS_SUMMARY = {
    "count": 0,
}

MOCK_TRACKER_ALERT = {
    "has_alert": False,
    "message": None,
    "recurring_meeting_id": None,
}

MOCK_LATEST_SUMMARY = {
    "available": False,
    "meeting_title": None,
    "action_item_count": 0,
    "created_at": None,
}

MOCK_REHEARSAL_CONTINUE = {
    "available": False,
    "session_id": None,
    "persona_name": None,
    "last_message_preview": None,
    "updated_at": None,
}
