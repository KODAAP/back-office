from django.urls import path

from core_apps.odk.views import (
    AppUserCreateView,
    AppUserListView,
    AppUserRevokeView,
    AppUsersFormView,
    CreateListAccessView,
    EnketoFormPreviewView,
    EnketoSubmissionEditView,
    FormCreateView,
    FormDeleteView,
    FormDetailView,
    FormDraftPublishView,
    FormDraftSubmissionsView,
    FormDraftView,
    FormSubmissionDetailView,
    FormSubmissionsExportView,
    FormSubmissionsListView,
    FormVersionsView,
    FormVersionXLSXDownloadView,
    FormVersionXMLView,
    FormXLSXDownloadView,
    MatrixView,
    ODKProjectListView,
    ProjectFormsListView,
    RevokeAccessLinkView,
    SubmissionsDataView,
    SubmissionsZipView,
)

app_name = "odk"

urlpatterns = [
    path("projects", ODKProjectListView.as_view(), name="projects-list"),
    # # Forms
    path("projects/<int:project_id>/forms/", FormCreateView.as_view(), name="add-form"),
    # List forms in a project
    path(
        "projects/<int:project_id>/forms",
        ProjectFormsListView.as_view(),
        name="project-forms-list",
    ),
    # Form details
    path(
        "projects/<int:project_id>/forms/<str:form_id>/",
        FormDetailView.as_view(),
        name="form-detail",
    ),
    # Download XLSX of a form (original Excel upload)
    path(
        "projects/<int:project_id>/forms/<str:form_id>/xlsx/",
        FormXLSXDownloadView.as_view(),
        name="form-download-xlsx",
    ),
    # Download XLSX of a specific form version
    path(
        "projects/<int:project_id>/forms/<str:form_id>/versions/<str:version>/xlsx/",
        FormVersionXLSXDownloadView.as_view(),
        name="form-version-download-xlsx",
    ),
    # Form deletion
    path(
        "projects/<int:project_id>/forms/<str:form_id>/delete/",
        FormDeleteView.as_view(),
        name="form-delete",
    ),
    # Submissions (published form)
    path(
        "projects/<int:project_id>/forms/<str:form_id>/submissions/",
        FormSubmissionsListView.as_view(),
        name="submissions-list",
    ),
    # Submissions CSV export JSON
    path(
        "projects/<int:project_id>/forms/<str:form_id>/submissions.csv",
        FormSubmissionsExportView.as_view(),
        name="submissions-csv",
    ),
    path(
        "projects/<int:project_id>/forms/<str:form_id>/submissions.zip",
        SubmissionsZipView.as_view(),
        name="submissions-zip",
    ),
    path(
        "projects/<int:project_id>/forms/<str:form_id>/submissions.json",
        SubmissionsDataView.as_view(),
        name="submissions-json",
    ),
    # Submission details
    path(
        "projects/<int:project_id>/forms/<str:form_id>/submissions/<str:instance_id>/",
        FormSubmissionDetailView.as_view(),
        name="form-submission-detail",
    ),
    # Enketo integration
    path(
        "projects/<int:project_id>/forms/<str:form_id>/preview-url/",
        EnketoFormPreviewView.as_view(),
        name="form-preview-url",
    ),
    path(
        "projects/<int:project_id>/forms/<str:form_id>/submissions/<str:instance_id>/edit-url/",
        EnketoSubmissionEditView.as_view(),
        name="submission-edit-url",
    ),
    # App Users
    path(
        "projects/<int:project_id>/app-users/",
        AppUserCreateView.as_view(),
        name="create-app-user",
    ),
    path(
        "projects/<int:project_id>/app-users",
        AppUserListView.as_view(),
        name="list-app-users",
    ),
    path(
        "projects/<int:project_id>/app-users/<str:token>/revoke/",
        AppUserRevokeView.as_view(),
        name="revoke-app-user",
    ),
    path(
        "projects/<int:project_id>/forms/<str:form_id>/app-users/<int:user_id>/",
        AppUsersFormView.as_view(),
        name="form-app-users",
    ),
    path(
        "projects/<int:project_id>/forms/<str:form_id>/app-users",
        AppUsersFormView.as_view(),
        name="form-user-list",
    ),
    path(
        "projects/<int:project_id>/matrix",
        MatrixView.as_view(),
        name="form-user-matrix",
    ),
    # ================================
    # MVP ROUTES FOR DRAFT MANAGEMENT
    # ================================
    # Draft management
    path(
        "projects/<int:project_id>/forms/<str:form_id>/draft/",
        FormDraftView.as_view(),
        name="form-draft",
    ),
    # Draft publishing
    path(
        "projects/<int:project_id>/forms/<str:form_id>/draft/publish/",
        FormDraftPublishView.as_view(),
        name="form-draft-publish",
    ),
    # Draft test submissions
    path(
        "projects/<int:project_id>/forms/<str:form_id>/draft/submissions/",
        FormDraftSubmissionsView.as_view(),
        name="form-draft-submissions",
    ),
    # Published version management
    path(
        "projects/<int:project_id>/forms/<str:form_id>/versions/",
        FormVersionsView.as_view(),
        name="form-versions",
    ),
    # XML for a specific version
    path(
        "projects/<int:project_id>/forms/<str:form_id>/versions/<str:version>.xml",
        FormVersionXMLView.as_view(),
        name="form-version-xml",
    ),
    # Public access to form definition
    path(
        "projects/<int:project_id>/forms/<str:form_id>/public-links/",
        CreateListAccessView.as_view(),
        name="form-public-links",
    ),
    path(
        "public-links/<str:token>/revoke/",
        RevokeAccessLinkView.as_view(),
        name="revoke-public-link",
    ),
]
