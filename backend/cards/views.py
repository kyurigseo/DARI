from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Card
from .serializers import CardSerializer


class CardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class CardListCreateView(generics.ListCreateAPIView):
    """
    GET: 최신순 카드 목록 (본인 소유만). raw ISO8601 created_at을 그대로 내려주고
    "N일 전" 변환은 프론트에서 계산한다 — 이유는 아래 참고.
    POST: rehearsal이 "카드로 저장" 액션에서 호출하는 저장 엔드포인트.
    """

    serializer_class = CardSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CardPagination

    def get_queryset(self):
        return Card.objects.filter(owner=self.request.user)


class CardDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_card(self, request, card_id):
        card = get_object_or_404(Card, id=card_id)
        if card.owner_id != request.user.id:
            raise PermissionDenied()
        return card

    def get(self, request, card_id):
        card = self._get_card(request, card_id)
        return Response(CardSerializer(card).data)

    def delete(self, request, card_id):
        card = self._get_card(request, card_id)
        card.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CardCountView(APIView):
    """홈 화면 '저장된 카드 개수' 카드용 경량 엔드포인트."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Card.objects.filter(owner=request.user).count()
        return Response({"count": count})
