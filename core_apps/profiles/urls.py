from django.urls import path

from .views import (
    AvatarUploadView,
    ProfileDetailAPIView,
    ProfileListAPIView,
    ProfileRoleUpdateAPIView,
    ProfileUpdateAPIView,
)

urlpatterns = [
    path("", ProfileListAPIView.as_view(), name="profile-list"),
    path("user/me/", ProfileDetailAPIView.as_view(), name="profile-detail"),
    path("user/update/", ProfileUpdateAPIView.as_view(), name="profile-update"),
    path("user/avatar/", AvatarUploadView.as_view(), name="avatar-upload"),
    path(
        "user/<int:pkid>/role/",
        ProfileRoleUpdateAPIView.as_view(),
        name="profile-role-update",
    ),
]
