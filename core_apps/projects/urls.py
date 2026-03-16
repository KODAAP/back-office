from django.urls import path

from core_apps.projects.views import (
    ProjectArchiveView,
    ProjectDetailView,
    ProjectListCreateView,
    ProjectPermissionAssignView,
    ProjectPermissionListView,
    ProjectPermissionRevokeView,
    ProjectRestoreView,
    ProjectUnarchiveView,
    UserProjectListView,
)

app_name = "projects"

urlpatterns = [
    path("", ProjectListCreateView.as_view(), name="project-list-create"),
    path("<int:pkid>/", ProjectDetailView.as_view(), name="project-detail"),
    path("<int:pk>/archive/", ProjectArchiveView.as_view(), name="project-archive"),
    path(
        "<int:pk>/unarchive/", ProjectUnarchiveView.as_view(), name="project-unarchive"
    ),
    path("<int:pk>/restore/", ProjectRestoreView.as_view(), name="project-restore"),
    path(
        "<int:pkid>/permissions/",
        ProjectPermissionListView.as_view(),
        name="list-permissions",
    ),
    path(
        "<int:pkid>/permissions/assign/",
        ProjectPermissionAssignView.as_view(),
        name="assign-permission",
    ),
    path(
        "<int:pkid>/permissions/<int:user_id>/revoke/",
        ProjectPermissionRevokeView.as_view(),
        name="revoke-permission",
    ),
    path(
        "users/<int:user_id>/projects/",
        UserProjectListView.as_view(),
        name="user-project-list",
    ),
]
