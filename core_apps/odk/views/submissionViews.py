import logging

from django.http import HttpResponse

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core_apps.common.renderers import GenericJSONRenderer
from core_apps.odk.mixins import ProjectValidationMixin
from core_apps.odk.services import ODKCentralService
from core_apps.odk.services.exceptions import ODKValidationError

logger = logging.getLogger(__name__)


class FormSubmissionsListView(ProjectValidationMixin, APIView):
    renderer_classes = [GenericJSONRenderer]
    object_label = "submissions"

    def get(self, request, project_id, form_id):
        """Retrieve all submissions for a specific form"""
        # Validate project access using mixin
        django_project, error_response = self.validate_project(project_id)
        if error_response:
            return error_response
        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_project_id = django_project.odk_id
                if not odk_project_id:
                    return Response(
                        {"error": "ODK project not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                submissions = odk_service.get_form_submissions(odk_project_id, form_id)
                return Response(
                    {"count": len(submissions), "results": submissions},
                    status=status.HTTP_200_OK,
                )
        except Exception as e:
            logger.error(f"Error getting form submissions: {e}")
            return Response(
                {"error": "Unable to get form submissions", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class FormSubmissionsExportView(ProjectValidationMixin, APIView):
    """Export all submissions of a form as CSV or XLSX"""

    renderer_classes = [GenericJSONRenderer]
    object_label = "submission"

    def post(self, request, project_id, form_id):
        django_project, error_response = self.validate_project(project_id)
        if error_response:
            return error_response

        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_project_id = django_project.odk_id
                if not odk_project_id:
                    return Response(
                        {"error": "ODK project not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                to = request.headers["to"] if "to" in request.headers else "csv"

                if to not in ["csv", "xlsx"]:
                    return Response(
                        {
                            "error": "Invalid format. Supported formats are 'csv' and 'xlsx'."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if to == "csv":
                    contentType = "text/csv"
                else:
                    contentType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

                file_bytes = odk_service.export_submissions(
                    odk_project_id, form_id, to=to
                )
                response = HttpResponse(
                    file_bytes,
                    content_type=contentType,
                )
                response["Content-Disposition"] = (
                    f'filename="{form_id}_submissions.{to}"'
                )
                return response

        except ODKValidationError:
            raise
        except Exception as e:
            logger.error(f"Error exporting submissions CSV: {e}")
            return Response(
                {"error": "Unable to export submissions CSV", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class FormSubmissionDetailView(ProjectValidationMixin, APIView):
    renderer_classes = [GenericJSONRenderer]
    object_label = "submission"

    def get(self, request, project_id, form_id, instance_id):
        """Retrieve details of a specific submission"""
        django_project, error_response = self.validate_project(project_id)
        if error_response:
            return error_response
        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_project_id = django_project.odk_id
                if not odk_project_id:
                    return Response(
                        {"error": "ODK project not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                submission = odk_service.get_submission(
                    odk_project_id, form_id, instance_id
                )
                return Response(submission, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting submission details: {e}")
            return Response(
                {"error": "Unable to get submission details", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SubmissionsDataView(ProjectValidationMixin, APIView):

    def get(self, request, project_id, form_id):
        project, error_response = self.validate_project(project_id)
        if error_response:
            return error_response
        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_id = project.odk_id
                if not odk_id:
                    return Response(
                        {"error": "ODK project not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                data = odk_service.submissions_data(odk_id, form_id)
                return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting submissions data: {e}")
            return Response(
                {"error": "Unable to get submissions data", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
