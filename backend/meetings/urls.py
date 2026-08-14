from django.urls import path
from .views import (
    CreateMeetingView,
    PrejoinView,
    MediaTokenView,
    SpeechCardListView,
    ParticipantManageView,
    KickParticipantView
    EndMeetingView
)

urlpatterns = [
    path('', CreateMeetingView.as_view(), name='create-meeting'),
    path('speech-cards/', SpeechCardListView.as_view(), name='speech-card-list'),
    path('<str:room_code>/prejoin/', PrejoinView.as_view(), name='prejoin-meeting'),
    path('<str:room_code>/token/', MediaTokenView.as_view(), name='media-token'),
    path('<str:room_code>/participants/', ParticipantManageView.as_view(), name='participant-manage'),
    path('<str:room_code>/kick/', KickParticipantView.as_view(), name='participant-kick'),
    path('<str:room_code>/end/', EndMeetingView.as_view(), name='end-meeting'),
]