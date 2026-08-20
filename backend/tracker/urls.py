from django.urls import path

from .views import (
    AlertsLatestView,
    HeatmapMeUpdateView,
    HeatmapView,
    MeetingConfirmView,
    ParticipationIngestView,
    ParticipationSummaryView,
    RecommendationView,
)

urlpatterns = [
    path("alerts/latest/", AlertsLatestView.as_view(), name="tracker-alerts-latest"),
    path("participation/summary/", ParticipationSummaryView.as_view(), name="tracker-participation-summary"),
    path("participation/ingest/", ParticipationIngestView.as_view(), name="tracker-participation-ingest"),
    path("heatmap/", HeatmapView.as_view(), name="tracker-heatmap"),
    path("heatmap/me/", HeatmapMeUpdateView.as_view(), name="tracker-heatmap-me"),
    path("recommendations/", RecommendationView.as_view(), name="tracker-recommendations"),
    path("meetings/confirm/", MeetingConfirmView.as_view(), name="tracker-meeting-confirm"),
]
