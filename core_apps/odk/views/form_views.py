import logging

from django.http import HttpResponse

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core_apps.common.renderers import GenericJSONRenderer
from core_apps.odk.services import ODKCentralService
from core_apps.odk.services.exceptions import ODKValidationError
from core_apps.projects.models import Projects

from ..cache import ODKCacheManager
from ..mixins import ProjectValidationMixin

logger = logging.getLogger(__name__)


class FormCreateView(APIView):
    renderer_classes = [
        GenericJSONRenderer,
    ]
    object_label = "project_form"

    # permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        """
        Handles the creation and uploading of an ODK form associated with a specific project. This includes checking the
        existence of the project in the database, validating the uploaded form file, and interacting with the ODK Central
        service to create the form and associate it with a corresponding ODK project. If necessary, the operation rolls back
        changes in case of failures.
        """
        created_new_odk_project = False
        odk_project_id = None
        try:
            # Check if the project exists in django db
            try:
                django_project = Projects.objects.get(pkid=project_id)
            except Projects.DoesNotExist:
                return Response(
                    {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
                )
            # Check et validate the file in the request
            form_file = request.FILES.get("form")
            if not form_file:
                return Response(
                    {"error": "Form file is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Get the file name and check extension
            filename = form_file.name
            file_extension = filename.split(".")[-1].lower()
            if file_extension not in ["xml", "xlsx", "xls"]:
                return Response(
                    {"error": "Invalid file extension"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            form_data = form_file.read()
            form_id = request.query_params.get("form_id")
            ignore_warnings = (
                request.query_params.get("ignore_warnings", "false").lower() == "true"
            )
            publish = request.query_params.get("publish", "false").lower() == "true"

            # Appel du service ODK
            with ODKCentralService(request.user, request=request) as odk_service:
                try:
                    # Check if django_project is a string before accessing odk_id attribute
                    # if isinstance(django_project, str):
                    #     return Response(
                    #         {"error": "Invalid project format"},
                    #         status=status.HTTP_400_BAD_REQUEST,
                    #     )
                    had_odk_project = django_project.odk_id is not None

                    odk_project_id = odk_service.ensure_odk_project_exists(
                        django_project
                    )
                    # logger.info("odk_project_id: %s", odk_project_id)
                    if not had_odk_project:
                        created_new_odk_project = True
                    form = odk_service.create_form(
                        odk_project_id,
                        form_data,
                        filename,
                        form_id=form_id,
                        ignore_warnings=ignore_warnings,
                        publish=False,  # Always create as draft first to allow version override
                    )

                    # If the user requested publication, publish it now with a guaranteed version
                    if publish:
                        xml_form_id = form.get("xmlFormId")
                        version_to_publish = form.get("version") or "1.0"
                        odk_service.publish_draft(
                            odk_project_id, xml_form_id, version=version_to_publish
                        )
                        # Refresh form details to reflect published status
                        form = odk_service.get_form(odk_project_id, xml_form_id)

                    ODKCacheManager.invalidate_project_cache(
                        request.user.id, odk_project_id
                    )
                    return Response({"form": form}, status=status.HTTP_201_CREATED)
                except ODKValidationError as e:
                    if created_new_odk_project:
                        self.rollback_project_creation(
                            odk_service, odk_project_id, django_project
                        )
                    return e.to_response(
                        error_message="Form validation error",
                        log_message=f"ODK validation error during form creation: {e}",
                    )
                except Exception as e:
                    if created_new_odk_project:
                        self.rollback_project_creation(
                            odk_service, odk_project_id, django_project
                        )
                    raise e
        except ODKValidationError as e:
            return e.to_response(
                error_message="Form validation error",
                log_message=f"ODK validation error during form creation: {e}",
            )
        except Exception as e:
            logger.error(f"Error creating form: {e}")
            return Response(
                {
                    "error": "Unable to create form",
                    "detail": str(e),
                    "message": "Form creation failed and all changes have been rolled back",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def rollback_project_creation(
        self, odk_service, odk_project_id, django_project
    ) -> None:
        try:
            logger.info(
                f"Rolling back ODK project creation for project {django_project.pkid}"
            )
            odk_service.delete_project(odk_project_id)
            django_project.odk_id = None
            django_project.save()
            logger.info(
                f"Successfully rolled back ODK project creation for project {django_project.pkid}"
            )
        except Exception as rollback_error:
            logger.error(f"Error rolling back ODK project creation: {rollback_error}")


class ProjectFormsListView(APIView):
    renderer_classes = [
        GenericJSONRenderer,
    ]
    object_label = "project_forms"

    # permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        """
        Handles the retrieval of all ODK forms associated with a specific project. This includes checking the existence
        of the project in the database and interacting with the ODK Central service to fetch the list of forms.
        """
        try:
            try:
                django_project = Projects.objects.get(pkid=project_id)
            except Projects.DoesNotExist:
                return Response(
                    {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
                )
            # Appel du service ODK
            with ODKCentralService(request.user, request=request) as odk_service:
                try:
                    forms = odk_service.get_project_forms(django_project.odk_id)

                    for form in forms:
                        form["publish"] = form.get("publishedAt") is not None
                        if form.get("publishedAt") is None:
                            form["submissions"] = 0
                        else:
                            form["submissions"] = len(
                                odk_service.get_form_submissions(
                                    django_project.odk_id, form["xmlFormId"]
                                )
                            )
                    return Response(
                        {"count": len(forms), "forms": forms}, status=status.HTTP_200_OK
                    )
                except Exception as e:
                    raise e
        except Exception as e:
            logger.error(f"Error listing forms: {e}")
            return Response(
                {
                    "error": "Unable to list forms",
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FormDetailView(APIView):
    renderer_classes = [
        GenericJSONRenderer,
    ]
    object_label = "form"

    def get(self, request, project_id, form_id):
        """
        Handles the retrieval of details for a specific ODK form. This includes checking the existence
        of the project in the database and interacting with the ODK Central service to fetch the form details.
        """
        try:
            try:
                django_project = Projects.objects.get(pkid=project_id)
            except Projects.DoesNotExist:
                return Response(
                    {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
                )

            # Appel du service ODK
            with ODKCentralService(request.user, request=request) as odk_service:
                try:
                    form_details = odk_service.get_form(django_project.odk_id, form_id)
                    return Response(form_details, status=status.HTTP_200_OK)
                except Exception as e:
                    if "404" in str(e):
                        return Response(
                            {"error": "Form not found"},
                            status=status.HTTP_404_NOT_FOUND,
                        )
                    raise e
        except Exception as e:
            logger.error(f"Error retrieving form details: {e}")
            return Response(
                {
                    "error": "Unable to retrieve form details",
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FormDeleteView(APIView):

    def delete(self, request, project_id, form_id):
        """
        Handles the deletion of a specific ODK form. This includes checking the existence
        of the project in the database and interacting with the ODK Central service to delete the form.
        The form is moved to trash and can be restored within 30 days.
        """
        try:
            try:
                django_project = Projects.objects.get(pkid=project_id)
            except Projects.DoesNotExist:
                return Response(
                    {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
                )

            # Appel du service ODK
            with ODKCentralService(request.user, request=request) as odk_service:
                try:
                    _ = odk_service.delete_form(django_project.odk_id, form_id)
                    # Invalidate cache after form deletion
                    ODKCacheManager.invalidate_project_cache(
                        request.user.id, django_project.odk_id
                    )
                    return Response(status=status.HTTP_204_NO_CONTENT)
                except Exception as e:
                    if "404" in str(e):
                        return Response(
                            {"error": "Form not found"},
                            status=status.HTTP_404_NOT_FOUND,
                        )
                    raise e
        except Exception as e:
            logger.error(f"Error deleting form: {e}")
            return Response(
                {
                    "error": "Unable to delete form",
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FormXLSXDownloadView(ProjectValidationMixin, APIView):
    """Download the XLSX source of a Form from ODK Central and stream it to the client."""

    def get(self, request, project_id: int, form_id: str):
        project, error_response = self.validate_project(project_id)
        if error_response:
            return error_response

        odk_project_id, odk_error = self.validate_odk_association(project)
        if odk_error:
            return odk_error

        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                content = odk_service.download_form_xlsx(odk_project_id, form_id)
                filename = request.query_params.get("filename") or f"{form_id}.xlsx"

                response = HttpResponse(
                    content,
                    content_type=(
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ),
                )
                response["Content-Disposition"] = f'attachment; filename="{filename}"'
                return response
        except Exception as e:
            msg = str(e).lower()
            if "404" in msg or "not found" in msg:
                return Response(
                    {"error": "Form or XLSX not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {"error": "Unable to download form XLSX", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class FormVersionXLSXDownloadView(ProjectValidationMixin, APIView):
    """Télécharge le fichier XLSX d'une version spécifique d'un formulaire depuis ODK Central et le diffuse au client."""

    def get(self, request, project_id: int, form_id: str, version: str):
        project, error_response = self.validate_project(project_id)
        if error_response:
            return error_response

        odk_project_id, odk_error = self.validate_odk_association(project)
        if odk_error:
            return odk_error

        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                content = odk_service.download_form_version_xlsx(
                    odk_project_id, form_id, version
                )
                filename = (
                    request.query_params.get("filename") or f"{form_id}_v{version}.xlsx"
                )

                response = HttpResponse(
                    content,
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                response["Content-Disposition"] = f'attachment; filename="{filename}"'
                return response
        except Exception as e:
            msg = str(e).lower()
            if "404" in msg or "not found" in msg:
                return Response(
                    {"error": "Form version or XLSX not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {"error": "Unable to download form version XLSX", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
