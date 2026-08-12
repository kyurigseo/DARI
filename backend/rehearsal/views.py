from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import ai_engine, cards_client
from .models import Persona, RehearsalFeedback, RehearsalMessage, RehearsalSession
from .serializers import (
    FeedbackSerializer,
    MessageSerializer,
    PersonaSerializer,
    SaveCardRequestSerializer,
    SessionMessageRequestSerializer,
    SessionStartRequestSerializer,
)


class PersonaListView(generics.ListAPIView):
    queryset = Persona.objects.filter(is_active=True)
    serializer_class = PersonaSerializer
    permission_classes = [permissions.IsAuthenticated]


class SessionStartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        req = SessionStartRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        persona = get_object_or_404(Persona, id=req.validated_data["persona_id"], is_active=True)

        session = RehearsalSession.objects.create(
            user=request.user, persona=persona, context=req.validated_data["context"]
        )
        opening_message = ai_engine.generate_opening_message(persona, session.context)
        RehearsalMessage.objects.create(session=session, role=RehearsalMessage.Role.AI, content=opening_message)
        quick_replies = ai_engine.generate_quick_replies(persona, opening_message)

        return Response(
            {
                "session_id": session.id,
                "persona": PersonaSerializer(persona).data,
                "opening_message": opening_message,
                "quick_replies": quick_replies,
            },
            status=status.HTTP_201_CREATED,
        )


class SessionMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(
            RehearsalSession, id=session_id, user=request.user, status=RehearsalSession.Status.ACTIVE
        )
        req = SessionMessageRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        user_text = req.validated_data["content"]

        user_message = RehearsalMessage.objects.create(
            session=session, role=RehearsalMessage.Role.USER, content=user_text
        )

        feedback_data = ai_engine.generate_feedback(session.persona, user_text)
        feedback = RehearsalFeedback.objects.create(
            session=session, user_message=user_message, original_text=user_text, **feedback_data
        )

        ai_reply = ai_engine.generate_ai_reply(session.persona, user_text)
        ai_message = RehearsalMessage.objects.create(
            session=session, role=RehearsalMessage.Role.AI, content=ai_reply
        )
        quick_replies = ai_engine.generate_quick_replies(session.persona, ai_reply)

        return Response(
            {
                "ai_message": MessageSerializer(ai_message).data,
                "feedback": FeedbackSerializer(feedback).data,
                "quick_replies": quick_replies,
            }
        )


class SessionEndView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(RehearsalSession, id=session_id, user=request.user)

        if session.status == RehearsalSession.Status.ACTIVE:
            session.status = RehearsalSession.Status.ENDED
            session.ended_at = timezone.now()
            session.duration_sec = int((session.ended_at - session.started_at).total_seconds())
            session.save(update_fields=["status", "ended_at", "duration_sec"])
        # 이미 종료된 세션 재호출은 멱등: 새로 계산하지 않고 저장된 결과를 그대로 반환

        feedback_list = FeedbackSerializer(session.feedbacks.all(), many=True).data
        return Response(
            {
                "session_id": session.id,
                "feedback_list": feedback_list,
                "duration_sec": session.duration_sec,
            }
        )


class FeedbackSaveCardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, feedback_id):
        feedback = get_object_or_404(
            RehearsalFeedback, id=feedback_id, session__user=request.user
        )

        if feedback.is_saved_as_card:
            return Response({"card_id": feedback.card_id}, status=status.HTTP_200_OK)

        req = SaveCardRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        category = req.validated_data["category"]

        try:
            card_id = cards_client.create_card(
                request,
                original_text=feedback.original_text,
                suggested_text=feedback.suggested_text,
                translated_text=feedback.translated_text,
                translated_language=feedback.translated_language,
                situation_label=feedback.situation_label,
                partner_tag=feedback.session.persona.name,
                category=category,
                explanation=feedback.explanation,
            )
        except cards_client.CardsUnavailable:
            return Response(
                {
                    "error": {
                        "code": "UPSTREAM_UNAVAILABLE",
                        "message": "카드함(cards) 서비스가 아직 준비되지 않아 저장하지 못했습니다. 잠시 후 다시 시도해주세요.",
                    }
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        feedback.is_saved_as_card = True
        feedback.card_id = str(card_id)
        feedback.category = category or "미분류"
        feedback.save(update_fields=["is_saved_as_card", "card_id", "category"])

        return Response({"card_id": card_id}, status=status.HTTP_201_CREATED)


class LatestSessionView(APIView):
    """home 앱이 호출하는 '이어하기' 조회용 (api.md 2번 섹션에서 합의된 제안 스펙)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        last_message = (
            RehearsalMessage.objects.filter(session__user=request.user)
            .order_by("-created_at")
            .select_related("session", "session__persona")
            .first()
        )
        if not last_message:
            return Response(
                {
                    "available": False,
                    "session_id": None,
                    "persona_name": None,
                    "last_message_preview": None,
                    "updated_at": None,
                }
            )

        session = last_message.session
        return Response(
            {
                "available": True,
                "session_id": session.id,
                "persona_name": session.persona.name,
                "last_message_preview": last_message.content[:80],
                "updated_at": last_message.created_at,
            }
        )
