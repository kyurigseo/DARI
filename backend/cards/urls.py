from django.urls import path

from .views import CardCountView, CardDetailView, CardListCreateView

urlpatterns = [
    path("", CardListCreateView.as_view(), name="card-list-create"),
    path("count/", CardCountView.as_view(), name="card-count"),
    path("<uuid:card_id>/", CardDetailView.as_view(), name="card-detail"),
]
