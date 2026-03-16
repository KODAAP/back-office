from django.urls import path

from .views import (
    AcceptInvitationView,
    BulkInvitationView,
    SendInvitationView,
    ValidateInvitationView,
)

urlpatterns = [
    path("send/", SendInvitationView.as_view(), name="send-invitation"),
    path("bulk/", BulkInvitationView.as_view(), name="bulk-invitation"),
    path("validate/", ValidateInvitationView.as_view(), name="validate-invitation"),
    path("accept/", AcceptInvitationView.as_view(), name="accept-invitation"),
]
