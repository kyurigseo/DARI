from django.conf import settings
from rest_framework.permissions import BasePermission


class IsInternalService(BasePermission):
    """
    meetings 앱이 회의 종료 후 발화 데이터를 넣어주는 ingest 엔드포인트 전용 권한.
    EndMeetingView는 백그라운드 threading.Thread에서 요약 파이프라인을 돌리는데,
    tracker로의 데이터 전달도 같은 방식(요청 유저 컨텍스트 없는 서버-투-서버 호출)일
    가능성이 높아 JWT가 아닌 공유 시크릿 헤더로 인증한다.

    요청 형식: Authorization: Internal <INTERNAL_SERVICE_TOKEN>
    """

    def has_permission(self, request, view):
        expected = getattr(settings, "INTERNAL_SERVICE_TOKEN", "")
        if not expected:
            return False
        provided = request.META.get("HTTP_AUTHORIZATION", "")
        return provided == f"Internal {expected}"
