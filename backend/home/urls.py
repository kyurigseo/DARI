from django.urls import path

from .views import HomeDashboardView

urlpatterns = [
    path("", HomeDashboardView.as_view(), name="home-dashboard"),
]
