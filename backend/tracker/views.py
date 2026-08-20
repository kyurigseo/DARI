from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import meetings_client, services
from .models import AvailabilitySlot, ParticipationRecord, ScheduledMeetingRequest
from .permissions import IsInternalService
from .serializers import (
    AvailabilitySlotSerializer,
    AvailabilitySlotUpsertSerializer,
    MeetingConfirmSerializer,
    ParticipantIdsQuerySerializer,
    ParticipationIngestSerializer,
)

User = get_user_model()


def _parse_participant_ids_query(request, default_to_self=True):
    raw = request.query_params.get("participant_ids", "")
    ids = [v.strip() for v in raw.split(",") if v.strip()]
    if not ids and default_to_self:
        ids = [str(request.user.id)]
    if settings.DARI_DEMO_MODE and (not ids or ids == [str(request.user.id)]):
        demo_ids = User.objects.filter(username__in=["지민", "Anna", "Yuki"]).values_list("id", flat=True)
        ids = [str(request.user.id), *(str(user_id) for user_id in demo_ids)]
    return ids


class AlertsLatestView(APIView):
    """
    홈 화면 "시차 형평성" 요약 카드용 경량 엔드포인트.
    home/clients.py의 fetch_tracker_alert가 이미 기대하고 있는 계약을 그대로 구현한다:
    GET /api/v1/tracker/alerts/latest/ -> {has_alert, message, recurring_meeting_id}
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(services.detect_bias_alert(request.user))


class ParticipationSummaryView(APIView):
    """
    "최근 6회 참여 시간대" 위젯용. ?participant_ids=<uuid,uuid,...> 로 여러 참가자를
    한 번에 조회할 수 있다(트래커 화면은 참가자별 프로그레스바를 여러 개 보여줌).
    지정하지 않으면 본인만 반환.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ids = _parse_participant_ids_query(request)
        users = {str(u.id): u for u in User.objects.filter(id__in=ids)}

        results = []
        for uid in ids:
            user = users.get(uid)
            if not user:
                continue
            summary = services.recent_participation_summary(user)
            results.append({"user_id": uid, "username": user.username, **summary})

        return Response({"results": results})


class ParticipationIngestView(APIView):
    """
    meetings -> tracker 연동 지점 (신규 제안 스펙).
    회의 종료 후 meetings가 참가자 지역 + 발화 시간 데이터를 이 엔드포인트로 전달한다.
    서버 간 호출이라 JWT가 아니라 공유 시크릿(Authorization: Internal <token>)으로 인증한다.
    상세 스펙은 serializers.ParticipationIngestSerializer 참고.
    """

    permission_classes = [IsInternalService]

    def post(self, request):
        serializer = ParticipationIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        known_user_ids = set(
            str(uid)
            for uid in User.objects.filter(
                id__in=[str(p["user_id"]) for p in data["participants"]]
            ).values_list("id", flat=True)
        )

        created, skipped = [], []
        for entry in data["participants"]:
            user_id = str(entry["user_id"])
            if user_id not in known_user_ids:
                skipped.append(user_id)
                continue
            record = ParticipationRecord.objects.create(
                participant_id=user_id,
                external_meeting_id=data["external_meeting_id"],
                meeting_title=data["meeting_title"],
                meeting_time_utc=data["meeting_time_utc"],
                local_timezone=entry["local_timezone"],
                local_region=entry["local_region"],
                speaking_duration_seconds=entry["speaking_duration_seconds"],
            )
            created.append(str(record.id))

        return Response(
            {"created": created, "skipped_unknown_user_ids": skipped},
            status=status.HTTP_201_CREATED,
        )


class HeatmapView(APIView):
    """
    "모두의 시간 찾기" 조회. ?participant_ids=<uuid,uuid,...> 로 여러 참가자의 행을 한 번에 받는다.
    타인 행은 조회만 가능해야 하므로 이 엔드포인트는 로그인만 되어 있으면 누구나 조회 가능하고,
    수정은 HeatmapMeUpdateView(본인 전용)로만 가능하다.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ids = _parse_participant_ids_query(request)
        users = list(User.objects.filter(id__in=ids))

        slots_by_user = {}
        for slot in AvailabilitySlot.objects.filter(participant_id__in=ids):
            slots_by_user.setdefault(str(slot.participant_id), []).append(
                {
                    "weekday": slot.weekday,
                    "half_hour_index": slot.half_hour_index,
                    "status": slot.status,
                }
            )

        results = [
            {
                "user_id": str(user.id),
                "username": user.username,
                "is_me": user.id == request.user.id,
                "slots": slots_by_user.get(str(user.id), []),
            }
            for user in users
        ]
        return Response({"results": results})


class HeatmapMeUpdateView(APIView):
    """
    본인 행 한 칸을 편한/보통/불편으로 저장. participant는 항상 request.user로 고정하며
    요청 바디의 다른 사용자 id는 받지 않는다 — 이게 "본인 행만 수정 가능"의 실제 강제 지점이다.
    """

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        serializer = AvailabilitySlotUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        slot, _ = AvailabilitySlot.objects.update_or_create(
            participant=request.user,
            weekday=data["weekday"],
            half_hour_index=data["half_hour_index"],
            defaults={"status": data["status"]},
        )
        return Response(AvailabilitySlotSerializer(slot).data)


class RecommendationView(APIView):
    """
    추천 시간대 계산. body: {"participant_ids": ["<uuid>", ...]} (본인 포함해서 넘길 것).
    알고리즘 설명은 services.rank_candidate_slots 문서 참고.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ParticipantIdsQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        participant_ids = [str(pid) for pid in serializer.validated_data["participant_ids"]]
        if settings.DARI_DEMO_MODE and participant_ids == [str(request.user.id)]:
            participant_ids = _parse_participant_ids_query(request)

        best = services.recommend_slot(participant_ids)
        if best is None:
            return Response({"recommendation": None})

        start_utc = services.next_occurrence_utc(best["weekday"], best["half_hour_index"])
        users = {str(u.id): u for u in User.objects.filter(id__in=participant_ids)}

        uncomfortable_set = set(best["uncomfortable_ids"])
        neutral_set = set(best["neutral_ids"])

        participants_view = []
        for pid in participant_ids:
            user = users.get(pid)
            if not user:
                continue
            if pid in uncomfortable_set:
                local_status = AvailabilitySlot.UNCOMFORTABLE
            elif pid in neutral_set:
                local_status = AvailabilitySlot.NEUTRAL
            elif pid in best["comfortable_ids"]:
                local_status = AvailabilitySlot.COMFORTABLE
            else:
                local_status = None  # 미응답

            local_tz = "UTC"
            record = (
                ParticipationRecord.objects.filter(participant_id=pid).order_by("-meeting_time_utc").first()
            )
            if record:
                local_tz = record.local_timezone

            participants_view.append(
                {
                    "user_id": pid,
                    "username": user.username,
                    "status": local_status,
                    "local_time": services.local_time_display(start_utc, local_tz),
                    "local_timezone": local_tz,
                }
            )

        response = {
            "recommendation": {
                "weekday": best["weekday"],
                "half_hour_index": best["half_hour_index"],
                "start_time_utc": start_utc.isoformat(),
                "start_time_kst": services.local_time_display(start_utc, "Asia/Seoul") + " (KST)",
                "uncomfortable_count": best["uncomfortable_count"],
                "neutral_count": best["neutral_count"],
                "comfortable_count": best["comfortable_count"],
                "missing_count": best["missing_count"],
                "participants": participants_view,
                "has_uncomfortable_participants": best["uncomfortable_count"] > 0,
            }
        }
        return Response(response)


class MeetingConfirmView(APIView):
    """
    "이 시간으로 일정 확정하기". meetings 앱에는 아직 예정 시각 필드가 없어서
    (meetings_client.py 상단 docstring 참고), 확정 정보는 tracker에 먼저 기록하고
    meetings에는 방 생성 + 참가자 초대로 최선을 다해 반영한다. meetings 쪽 호출이
    실패해도 확정 기록 자체는 남기고 meetings_sync_status로 실패를 알린다.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MeetingConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        start_utc = services.next_occurrence_utc(data["weekday"], data["half_hour_index"])
        participant_ids = [str(pid) for pid in data["participant_ids"]]
        if str(request.user.id) not in participant_ids:
            participant_ids.append(str(request.user.id))

        scheduled = ScheduledMeetingRequest.objects.create(
            requested_by=request.user,
            title=data["title"],
            scheduled_start_time_utc=start_utc,
            participant_ids=participant_ids,
        )

        room_code = meetings_client.generate_room_code(data["title"])
        invite_errors = []
        try:
            meeting = meetings_client.create_meeting(request, title=data["title"], room_code=room_code)
            for pid in participant_ids:
                if pid == str(request.user.id):
                    continue  # 호스트는 CreateMeetingView가 이미 처리
                try:
                    meetings_client.invite_participant(request, room_code=room_code, user_id=pid)
                except meetings_client.MeetingsUnavailable as exc:
                    invite_errors.append(str(exc))

            scheduled.room_code = room_code
            scheduled.meetings_sync_status = (
                ScheduledMeetingRequest.SYNC_SYNCED if not invite_errors else ScheduledMeetingRequest.SYNC_FAILED
            )
            scheduled.meetings_sync_error = "; ".join(invite_errors)
            scheduled.save(update_fields=["room_code", "meetings_sync_status", "meetings_sync_error"])
            meeting_id = meeting.get("id")
        except meetings_client.MeetingsUnavailable as exc:
            scheduled.meetings_sync_status = ScheduledMeetingRequest.SYNC_FAILED
            scheduled.meetings_sync_error = str(exc)
            scheduled.save(update_fields=["meetings_sync_status", "meetings_sync_error"])
            meeting_id = None

        return Response(
            {
                "scheduled_meeting_request_id": str(scheduled.id),
                "title": scheduled.title,
                "room_code": scheduled.room_code,
                "meeting_id": meeting_id,
                "scheduled_start_time_utc": start_utc.isoformat(),
                "scheduled_start_time_kst": services.local_time_display(start_utc, "Asia/Seoul") + " (KST)",
                "participant_ids": participant_ids,
                "meetings_sync_status": scheduled.meetings_sync_status,
                "meetings_sync_error": scheduled.meetings_sync_error,
            },
            status=status.HTTP_201_CREATED,
        )
