import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core_apps.common.renderers import GenericJSONRenderer
from core_apps.odk.mixins import ProjectValidationMixin
from core_apps.odk.services import ODKCentralService

logger = logging.getLogger(__name__)

# class EnketoFormSurveyView(ProjectValidationMixin, APIView):
#     """Expose un endpoint pour obtenir l'URL Enketo de saisie d'un formulaire."""
#     renderer_classes = [GenericJSONRenderer]
#     object_label = "enketo_url"
#
#     def get(self, request, project_id, form_id):
#         """Retourne l'URL Enketo de saisie pour un formulaire.
#
#         Args:
#             request: Requête HTTP Django/DRF.
#             project_id (int): Identifiant du projet Django.
#             form_id (str): Identifiant XML du formulaire (xformId).
#
#         Returns:
#             Response: JSON contenant `{ "url": "..." }`.
#         """
#         django_project, error_response = self.validate_project(project_id)
#         if error_response:
#             return error_response
#
#         try:
#             with ODKCentralService(request.user, request=request) as odk_service:
#                 odk_project_id = django_project.odk_id
#                 if not odk_project_id:
#                     return Response(
#                         {"error": "ODK project not found"},
#                         status=status.HTTP_404_NOT_FOUND,
#                     )
#
#                 return_url = request.query_params.get("return_url")
#
#                 # On utilise l'Enketo local par défaut
#                 url = odk_service.get_survey_link(
#                     odk_project_id,
#                     form_id,
#                     local=True,
#                     return_url=return_url,
#                 )
#                 return Response({"url": url}, status=status.HTTP_200_OK)
#         except Exception as e:
#             logger.error(f"Error getting Enketo survey URL: {e}")
#             return Response(
#                 {"error": "Unable to get Enketo survey URL", "detail": str(e)},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )


class EnketoFormPreviewView(ProjectValidationMixin, APIView):
    """Expose un endpoint pour obtenir l'URL Enketo de prévisualisation d'un formulaire."""

    renderer_classes = [GenericJSONRenderer]
    object_label = "enketo_url"

    def get(self, request, project_id, form_id):
        """Retourne l'URL Enketo de prévisualisation pour un formulaire.

        Args:
            request: Requête HTTP Django/DRF.
            project_id (int): Identifiant du projet Django.
            form_id (str): Identifiant XML du formulaire (xformId).

        Returns:
            Response: JSON contenant `{ "url": "..." }`.
        """
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

                url = odk_service.get_preview_link(odk_project_id, form_id, local=True)
                return Response({"url": url}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting Enketo preview URL: {e}")
            return Response(
                {"error": "Unable to get Enketo preview URL", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class EnketoSubmissionEditView(ProjectValidationMixin, APIView):
    """Expose un endpoint pour obtenir l'URL Enketo d'édition d'une soumission."""

    renderer_classes = [GenericJSONRenderer]
    object_label = "enketo_url"

    def get(self, request, project_id, form_id, instance_id):
        """Retourne l'URL Enketo d'édition pour une soumission.

        Args:
            request: Requête HTTP Django/DRF.
            project_id (int): Identifiant du projet Django.
            form_id (str): Identifiant XML du formulaire (xformId).
            instance_id (str): Identifiant de la soumission.

        Returns:
            Response: JSON contenant `{ "url": "..." }`.
        """
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

                # On peut optionnellement passer un return_url
                return_url = request.query_params.get("return_url")

                url = odk_service.get_edit_link(
                    odk_project_id,
                    form_id,
                    instance_id,
                    local=True,
                    return_url=return_url,
                )
                return Response({"url": url}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting Enketo edit URL: {e}")
            return Response(
                {"error": "Unable to get Enketo edit URL", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
