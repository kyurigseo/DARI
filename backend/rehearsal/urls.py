from django.urls import path

from .views import (
    FeedbackSaveCardView,
    LatestSessionView,
    PersonaListView,
    SessionEndView,
    SessionMessageView,
    SessionStartView,
)

urlpatterns = [
    path("personas/", PersonaListView.as_view(), name="persona-list"),
    path("sessions/", SessionStartView.as_view(), name="session-start"),
    path("sessions/latest/", LatestSessionView.as_view(), name="session-latest"),
    path("sessions/<uuid:session_id>/messages/", SessionMessageView.as_view(), name="session-messages"),
    path("sessions/<uuid:session_id>/end/", SessionEndView.as_view(), name="session-end"),
    path("feedback/<uuid:feedback_id>/save-card/", FeedbackSaveCardView.as_view(), name="feedback-save-card"),
]
