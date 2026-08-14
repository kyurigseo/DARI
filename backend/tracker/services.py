"""
tracker 앱의 순수 계산 로직: 시간대 분류 / 편중 경고 판정 / 추천 시간대 계산.
views.py는 이 모듈의 함수만 호출하고 쿼리 조합 이상의 판단 로직은 여기에 둔다.

시간대(버킷) 정의 (참가자 로컬 시각 기준)
------------------------------------------------
- DAWN(새벽)    00:00 ~ 05:59
- DAYTIME(주간) 06:00 ~ 17:59  (12시간 — 업무/일상 활동 시간대는 형평성 문제가 크지 않다고 보고 넓게 묶음)
- EVENING(저녁) 18:00 ~ 23:59
CLAUDE.md 예시 문구("새벽 03~06시")는 배너 문구 예시일 뿐이라, 새벽에 걸치는 회의를
폭넓게 잡기 위해 새벽 구간을 00시부터로 넓혀 정의했다.

편중 경고 기준 (하드코딩)
------------------------------------------------
- RECENT_WINDOW = 6        : "최근 6회 참여" 요구사항 그대로.
- MIN_RECORDS_FOR_ALERT = 4 : 표본이 1~3회뿐이면 우연히 한 시간대에 몰릴 수 있어 오탐 방지용 최소 표본.
- WARNING_RATIO = 4/6(~66.7%) : CLAUDE.md 예시("6번 중 5번")보다 한 단계 낮춰, 4/6부터 조기 경고.
- ALERT_ELIGIBLE_BUCKETS = (DAWN, EVENING) : DAYTIME 쏠림은 경고 대상이 아님(정상적인 근무시간 회의이므로).
"""

from collections import Counter
from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone as dj_timezone

from .models import AvailabilitySlot, ParticipationRecord

DAWN, DAYTIME, EVENING = "DAWN", "DAYTIME", "EVENING"
BUCKET_LABELS = {DAWN: "새벽", DAYTIME: "주간", EVENING: "저녁"}
BUCKET_HOUR_RANGE = {DAWN: "00~06시", DAYTIME: "06~18시", EVENING: "18~24시"}
ALL_BUCKETS = (DAWN, DAYTIME, EVENING)

RECENT_WINDOW = 6
MIN_RECORDS_FOR_ALERT = 4
WARNING_RATIO = 4 / 6
ALERT_ELIGIBLE_BUCKETS = (DAWN, EVENING)

UTC = ZoneInfo("UTC")
KST = ZoneInfo("Asia/Seoul")


def _safe_zone(tz_name):
    try:
        return ZoneInfo(tz_name or "UTC")
    except ZoneInfoNotFoundError:
        return UTC


def classify_bucket(meeting_time_utc, local_timezone):
    """UTC datetime을 참가자 로컬 타임존으로 변환해 새벽/주간/저녁 버킷을 반환."""
    local_dt = meeting_time_utc.astimezone(_safe_zone(local_timezone))
    hour = local_dt.hour
    if hour < 6:
        return DAWN
    if hour < 18:
        return DAYTIME
    return EVENING


def recent_participation_summary(user, window=RECENT_WINDOW):
    """"최근 N회 참여 시간대" 위젯용 집계. 프로그레스바 라벨(예: 새벽 5/6)에 바로 쓸 수 있는 형태."""
    records = list(
        ParticipationRecord.objects.filter(participant=user).order_by("-meeting_time_utc")[:window]
    )
    counts = Counter(classify_bucket(r.meeting_time_utc, r.local_timezone) for r in records)
    total = len(records)
    buckets = {
        bucket: {
            "label": BUCKET_LABELS[bucket],
            "count": counts.get(bucket, 0),
            "ratio": round(counts.get(bucket, 0) / total, 4) if total else 0.0,
        }
        for bucket in ALL_BUCKETS
    }
    return {"window": window, "total_records": total, "buckets": buckets}


def detect_bias_alert(user, window=RECENT_WINDOW):
    """
    경고 배너 판정. 반환 형식은 home 앱이 이미 기대하고 있는
    GET /api/v1/tracker/alerts/latest/ 계약(has_alert, message, recurring_meeting_id)과 동일하다.
    """
    records = list(
        ParticipationRecord.objects.filter(participant=user).order_by("-meeting_time_utc")[:window]
    )
    total = len(records)
    empty = {"has_alert": False, "message": "", "recurring_meeting_id": None}
    if total < MIN_RECORDS_FOR_ALERT:
        return empty

    bucketed = [(r, classify_bucket(r.meeting_time_utc, r.local_timezone)) for r in records]
    counts = Counter(b for _, b in bucketed)

    dominant_bucket, dominant_count = None, 0
    for bucket in ALERT_ELIGIBLE_BUCKETS:
        if counts.get(bucket, 0) > dominant_count:
            dominant_bucket, dominant_count = bucket, counts[bucket]

    if not dominant_bucket or dominant_count / total < WARNING_RATIO:
        return empty

    matching_ids = {
        r.external_meeting_id for r, b in bucketed if b == dominant_bucket and r.external_meeting_id
    }
    recurring_meeting_id = matching_ids.pop() if len(matching_ids) == 1 else None

    message = (
        f"{user.username}님이 최근 {total}회 회의 중 {dominant_count}회, "
        f"{BUCKET_LABELS[dominant_bucket]} 시간대({BUCKET_HOUR_RANGE[dominant_bucket]})에 참여했어요."
    )
    return {"has_alert": True, "message": message, "recurring_meeting_id": recurring_meeting_id}


# ---------------------------------------------------------------------------
# 추천 시간대 계산
# ---------------------------------------------------------------------------
# 알고리즘: 주간 반복 336개(7일 x 48슬롯) 후보 슬롯 전부에 대해 참가자 전원의 상태를 모으고
#   1순위: 불편(UNCOMFORTABLE) 인원 수 최소화
#   2순위: 미응답(해당 슬롯에 아무 상태도 기록 안 한 참가자) 인원 수 최소화
#   3순위: 보통(NEUTRAL) 인원 수 최소화 (= 편한 인원 최대화와 사실상 동치)
#   4순위: weekday, half_hour_index 오름차순 (완전 동점일 때 결과를 결정적으로 만들기 위함 +
#          이왕이면 이른 시간을 우선 추천)
# CLAUDE.md 요청사항 "불편 인원 최소화 우선, 그다음 보통 인원 최소화"를 1·3순위로 채택했고,
# 미응답 최소화를 그 사이(2순위)에 끼워 넣은 이유는: 아무도 응답 안 한 슬롯은 uncomfortable=0,
# neutral=0이라 "가장 좋은 슬롯"으로 착시를 일으키기 쉬운데, 미응답을 neutral보다 먼저 비교해야
# 실제로 누군가 응답한(그 응답이 설령 neutral이더라도) 슬롯이 정보가 아예 없는 빈 슬롯보다
# 앞선다 — 정보가 없는 것과 실제로 "보통"이라고 답한 것은 다르다. (neutral을 미응답보다 먼저
# 비교하면 빈 슬롯의 neutral_count가 항상 0이라 오히려 빈 슬롯이 이겨버리는 버그가 있었다.)


def _slot_status_map(participant_ids):
    slots = AvailabilitySlot.objects.filter(participant_id__in=participant_ids)
    by_slot = {}
    for slot in slots:
        key = (slot.weekday, slot.half_hour_index)
        by_slot.setdefault(key, {}).setdefault(slot.status, []).append(str(slot.participant_id))
    return by_slot


def rank_candidate_slots(participant_ids):
    """모든 (weekday, half_hour_index) 후보를 우선순위대로 정렬해 반환."""
    by_slot = _slot_status_map(participant_ids)
    total_participants = len(participant_ids)

    candidates = []
    for weekday in range(7):
        for half_hour_index in range(48):
            statuses = by_slot.get((weekday, half_hour_index), {})
            uncomfortable = statuses.get(AvailabilitySlot.UNCOMFORTABLE, [])
            neutral = statuses.get(AvailabilitySlot.NEUTRAL, [])
            comfortable = statuses.get(AvailabilitySlot.COMFORTABLE, [])
            answered = len(uncomfortable) + len(neutral) + len(comfortable)
            candidates.append(
                {
                    "weekday": weekday,
                    "half_hour_index": half_hour_index,
                    "uncomfortable_count": len(uncomfortable),
                    "neutral_count": len(neutral),
                    "comfortable_count": len(comfortable),
                    "missing_count": total_participants - answered,
                    "uncomfortable_ids": uncomfortable,
                    "neutral_ids": neutral,
                    "comfortable_ids": comfortable,
                }
            )

    candidates.sort(
        key=lambda c: (
            c["uncomfortable_count"],
            c["missing_count"],
            c["neutral_count"],
            c["weekday"],
            c["half_hour_index"],
        )
    )
    return candidates


def recommend_slot(participant_ids):
    candidates = rank_candidate_slots(participant_ids)
    return candidates[0] if candidates else None


def next_occurrence_utc(weekday, half_hour_index, now=None):
    """주어진 (UTC 기준 weekday, half_hour_index)가 가리키는 다음 실제 발생 시각(UTC)을 계산."""
    now_utc = (now or dj_timezone.now()).astimezone(UTC)
    target_minutes = half_hour_index * 30
    days_ahead = (weekday - now_utc.weekday()) % 7
    candidate = (now_utc + timedelta(days=days_ahead)).replace(
        hour=target_minutes // 60, minute=target_minutes % 60, second=0, microsecond=0
    )
    if candidate <= now_utc:
        candidate += timedelta(days=7)
    return candidate


def local_time_display(utc_dt, tz_name):
    local_dt = utc_dt.astimezone(_safe_zone(tz_name))
    return local_dt.strftime("%Y-%m-%d %H:%M")
