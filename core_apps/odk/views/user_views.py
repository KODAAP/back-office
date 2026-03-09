import logging

from django.conf import settings

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core_apps.common.renderers import GenericJSONRenderer
from core_apps.odk.mixins import ProjectValidationMixin
from core_apps.odk.services import ODKCentralService
from core_apps.odk.services.app_user_services import ODKAppUserService
from core_apps.odk.utils import generate_odk_qr_code
from core_apps.projects.models import Projects

logger = logging.getLogger(__name__)


# TODO: Create one class view to do all the job: AppUserView with get, post, delete methods
class AppUserListView(APIView):
    renderer_classes = [
        GenericJSONRenderer,
    ]
    object_label = "app_users"

    def get(self, request, project_id):
        """
        Handles the retrieval of ODK app users associated with a specific project.
        This includes checking the existence of the project in the database and
        interacting with the ODK Central service to fetch the app users.
        """
        try:
            # Check if the project exists in django db
            try:
                django_project = Projects.objects.get(pkid=project_id)
            except Projects.DoesNotExist:
                return Response(
                    {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
                )
            # Check if odk_id exists for the project
            if not django_project.odk_id:
                return Response(
                    {"error": "Project is not associated with ODK"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Get app users using the service
            with ODKAppUserService(request.user, request=request) as app_user_service:
                try:
                    app_users = app_user_service.get_project_app_users(
                        django_project.odk_id
                    )
                    for app_user in app_users:
                        try:
                            server_url = getattr(
                                settings, "ODK_CENTRAL_URL", "https://odk.insuco.net"
                            )
                            # Remove /v1 from server_url if present for QR code generation
                            base_server_url = server_url.replace("/v1", "")
                            if app_user.get("token") is not None:
                                qr_code = generate_odk_qr_code(
                                    server_url=base_server_url,
                                    app_user_token=app_user.get("token"),
                                    project_id=django_project.odk_id,
                                    project_name=django_project.name,
                                )
                                app_user["qr_code"] = qr_code
                            else:
                                app_user["qr_code"] = None
                        except Exception as qr_error:
                            logger.warning(f"Failed to generate QR code: {qr_error}")
                            # Continue without QR code if generation fails
                            pass
                    return Response(
                        {"count": len(app_users), "results": app_users},
                        status=status.HTTP_200_OK,
                    )
                except Exception as e:
                    raise e
        except Exception as e:
            logger.error(f"Error retrieving app users: {e}")
            return Response(
                {
                    "error": "Unable to retrieve app users",
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AppUserCreateView(APIView):
    renderer_classes = [
        GenericJSONRenderer,
    ]
    object_label = "app_user"

    def post(self, request, project_id):
        """
        Handles the creation of an ODK app user associated with a specific project.
        This includes checking the existence of the project in the database and
        interacting with the ODK Central service to create the app user.
        """
        try:
            # Check if the project exists in django db
            try:
                django_project = Projects.objects.get(pkid=project_id)
            except Projects.DoesNotExist:
                return Response(
                    {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
                )
            # Check if odk_id exists for the project
            if not django_project.odk_id:
                return Response(
                    {"error": "Project is not associated with ODK"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Get display_name from request data
            display_name = request.data.get("display_name")
            if not display_name:
                return Response(
                    {"error": "Display name is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            with ODKAppUserService(request.user, request=request) as app_user_service:
                try:
                    app_user = app_user_service.create_app_user(
                        django_project.odk_id, display_name
                    )

                    return Response(app_user, status=status.HTTP_201_CREATED)
                except Exception as e:
                    raise e
        except Exception as e:
            logger.error(f"Error creating app user: {e}")
            return Response(
                {
                    "error": "Unable to create app user",
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AppUserRevokeView(ProjectValidationMixin, APIView):
    """View to revoke (delete) an ODK app user associated with a project"""

    def delete(self, request, project_id, token):
        project, error_response = self.validate_project(project_id)
        if error_response:
            return error_response
        try:
            with ODKAppUserService(request.user, request=request) as app_user_service:
                odk_project_id, error_response = self.validate_odk_association(project)
                if error_response:
                    return error_response
                app_user_service.revoke_app_user_access(odk_project_id, token)
                return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error revoking app user: {e}")
            return Response(
                {"error": "Unable to revoke app user", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AppUsersFormView(ProjectValidationMixin, APIView):
    """View to manage assignments of ODK forms to app users"""

    renderer_classes = [
        GenericJSONRenderer,
    ]

    @property
    def object_label(self):
        if self.request.method == "POST":
            return "assignment"
        elif self.request.method == "GET":
            return "assignments"
        return "assignment"

    def post(self, request, project_id: int, user_id: int, form_id: str):
        project, error_response = self.validate_project(project_id)
        if error_response:
            return error_response
        try:
            with ODKAppUserService(request.user, request=request) as app_user_service:
                odk_project_id, error_response = self.validate_odk_association(project)
                if error_response:
                    return error_response
                app_user_service.assign_form_to_user(odk_project_id, form_id, user_id)
                return Response(
                    {"detail": "Form assigned to app user successfully"},
                    status=status.HTTP_200_OK,
                )
        except Exception as e:
            logger.error(f"Error assigning form to app user: {e}")
            return Response(
                {"error": "Unable to assign form to app user", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get(self, request, project_id: int, form_id: str):
        project, error_response = self.validate_project(project_id)
        if error_response:
            return error_response
        try:
            with ODKAppUserService(request.user, request=request) as app_user_service:
                odk_project_id, error_response = self.validate_odk_association(project)
                if error_response:
                    return error_response
                app_users = app_user_service.list_forms_app_users(
                    odk_project_id, form_id
                )
                return Response(
                    {"count": len(app_users), "results": app_users},
                    status=status.HTTP_200_OK,
                )
        except Exception as e:
            logger.error(f"Error retrieving app users for form: {e}")
            return Response(
                {"error": "Unable to retrieve app users for form", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def delete(self, request, project_id: int, user_id: int, form_id: str):
        project, error_response = self.validate_project(project_id)
        if error_response:
            return error_response
        try:
            with ODKAppUserService(request.user, request=request) as app_user_service:
                odk_project_id, error_response = self.validate_odk_association(project)
                if error_response:
                    return error_response
                app_user_service.unassgin_form_to_user(odk_project_id, form_id, user_id)
                return Response(
                    {"detail": "Form unassigned from app user successfully"},
                    status=status.HTTP_204_NO_CONTENT,
                )
        except Exception as e:
            logger.error(f"Error unassigning form from app user: {e}")
            return Response(
                {"error": "Unable to unassign form from app user", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MatrixView(ProjectValidationMixin, APIView):
    """
      View to get a matrix of form assignments to app users.
      The matrix indicates which forms are assigned to which app users.
      Response format:
    [
      appuserId1: { formId1: true, formId2: false, ... },
      appuserId2: { formId1: true, formId2: true, ... },
      ...
    ]
    """

    def get(self, request, project_id: int):
        project, error_response = self.validate_project(project_id)
        if error_response:
            return error_response
        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_project_id, error_response = self.validate_odk_association(project)
                if error_response:
                    return error_response
                app_users = odk_service.get_project_app_users(odk_project_id)
                forms = odk_service.get_project_forms(odk_project_id)
                matrix = {}
                for app_user in app_users:
                    if app_user["token"] is None:
                        continue
                    user_id = app_user.get("id")
                    matrix[user_id] = {}
                    for form in forms:
                        form_id = form.get("xmlFormId")
                        assigned_users = odk_service.list_forms_app_users(
                            odk_project_id, form_id
                        )
                        assigned_user_ids = [user.get("id") for user in assigned_users]
                        matrix[user_id][form_id] = user_id in assigned_user_ids
                return Response(matrix, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving assignment matrix: {e}")
            return Response(
                {"error": "Unable to retrieve assignment matrix", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
