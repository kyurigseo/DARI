# 회의 API URL 라우팅

from django.urls import path
from .views import CreateMeetingView, PrejoinView, MediaTokenView

urlpatterns = [
    path('', CreateMeetingView.as_view(), name='create-meeting'),
    path('<str:room_code>/prejoin/', PrejoinView.as_view(), name='prejoin-meeting'),
    path('<str:room_code>/token/', MediaTokenView.as_view(), name='media-token'),
]