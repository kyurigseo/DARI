from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from . import clients


class HomeDashboardView(APIView):
    """
    홈 화면 대시보드. rehearsal/cards/tracker/meetings/summary 각 앱의 API를 호출해
    응답을 하나로 합친다 — 다른 앱의 모델/DB는 직접 참조하지 않는다.
    각 하위 항목은 독립적으로 실패를 흡수하므로, 특정 앱 API가 아직 없거나 오류가 나도
    해당 카드만 목업/빈 상태로 표시되고 홈 전체 응답은 항상 200으로 내려간다.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        meetings = clients.fetch_today_meetings(request)
        cards = clients.fetch_cards_summary(request)
        tracker = clients.fetch_tracker_alert(request)
        summary = clients.fetch_latest_summary(request)
        rehearsal = clients.fetch_rehearsal_continue(request)

        next_meeting = meetings["results"][0] if meetings["results"] else None

        return Response(
            {
                "greeting": f"안녕하세요, {request.user.username}님",
                "today_meeting_count": meetings["count"],
                "today_meetings": meetings["results"],
                "quick_stats": {
                    "speech_card": cards,
                    "tracker_alert": tracker,
                    "latest_summary": summary,
                    "rehearsal_continue": rehearsal,
                },
                "nav": {
                    "speech_card_badge_count": cards["count"],
                    "next_meeting_badge": next_meeting,
                },
            }
        )
