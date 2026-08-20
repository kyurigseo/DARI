from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    SignupView,
    MeView,
    MyPageDetailView,
    UserSettingsUpdateView,
    LogoutView
)

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path('mypage/', MyPageDetailView.as_view(), name='mypage-detail'),
    path('mypage/settings/', UserSettingsUpdateView.as_view(), name='mypage-settings-update'),
    path('logout/', LogoutView.as_view(), name='logout'),

]
