from django.urls import path
from .views import (
    CreateMeetingView,
    PrejoinView,
    MediaTokenView,
    SpeechCardListView,
    ParticipantManageView,
    KickParticipantView,
    EndMeetingView,
    UserMeetingListView,
    MeetingReportDetailView,
    MeetingMemoListCreateView,
    MeetingMemoDeleteView,
    ActionItemUpdateView,
    MeetingShareTextView,
    MeetingEmailSendView,
    HomeMeetingListView
)

urlpatterns = [
    path('', CreateMeetingView.as_view(), name='create-meeting'),
    path('speech-cards/', SpeechCardListView.as_view(), name='speech-card-list'),
    path('<str:room_code>/prejoin/', PrejoinView.as_view(), name='prejoin-meeting'),
    path('<str:room_code>/token/', MediaTokenView.as_view(), name='media-token'),
    path('<str:room_code>/participants/', ParticipantManageView.as_view(), name='participant-manage'),
    path('<str:room_code>/kick/', KickParticipantView.as_view(), name='participant-kick'),
    path('<str:room_code>/end/', EndMeetingView.as_view(), name='end-meeting'),
    path('summary-tabs/', UserMeetingListView.as_view(), name='user-meeting-tabs'),
    path('<str:room_code>/report/', MeetingReportDetailView.as_view(), name='meeting-report-detail'),
    path('<str:room_code>/memos/', MeetingMemoListCreateView.as_view(), name='meeting-memos'),
    path('memos/<uuid:memo_id>/', MeetingMemoDeleteView.as_view(), name='meeting-memo-delete'),
    path('action-items/<uuid:item_id>/', ActionItemUpdateView.as_view(), name='action-item-update'),
    path('<str:room_code>/share-text/', MeetingShareTextView.as_view(), name='meeting-share-text'),
    path('<str:room_code>/send-email/', MeetingEmailSendView.as_view(), name='meeting-send-email'),
    path('home/', HomeMeetingListView.as_view(), name='home-meetings'),
]
