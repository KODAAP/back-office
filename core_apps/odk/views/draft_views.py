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

logger = logging.getLogger(__name__)


class FormDraftView(APIView):
    """View for form draft management"""

    renderer_classes = [GenericJSONRenderer]
    object_label = "form_draft"

    def get_renderers(self):
        if self.request.method == "DELETE":
            from rest_framework.renderers import JSONRenderer

            return [JSONRenderer()]
        return super().get_renderers()

    def get(self, request, project_id, form_id):
        """Retrieve draft details"""
        try:
            django_project = Projects.objects.get(pkid=project_id)
        except Projects.DoesNotExist:
            return Response(
                {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
            )
        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_project_id = django_project.odk_id
                if not odk_project_id:
                    return Response(
                        {"error": "ODK project not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                draft_data = odk_service.get_form_draft(odk_project_id, form_id)

                return Response(draft_data, status=status.HTTP_200_OK)

        except ODKValidationError:
            raise
        except Exception as e:
            logger.error(f"Error getting draft: {e}")
            return Response(
                {"error": "Unable to get draft", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request, project_id, form_id):
        """Create or update a draft"""
        try:
            django_project = Projects.objects.get(pkid=project_id)
        except Projects.DoesNotExist:
            return Response(
                {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
            )

        form_file = request.FILES.get("form")
        if not form_file:
            return Response(
                {"error": "Form file is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        filename = form_file.name
        file_extension = filename.split(".")[-1].lower()
        if file_extension not in ["xml", "xlsx", "xls"]:
            return Response(
                {"error": "Invalid file extension"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        form_data = form_file.read()
        ignore_warnings = request.query_params.get("ignore_warnings", "true")

        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_project_id = django_project.odk_id
                if not odk_project_id:
                    return Response(
                        {"error": "ODK project not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                draft = odk_service.create_or_update_draft(
                    odk_project_id,
                    form_id,
                    form_data,
                    filename,
                    ignore_warnings=ignore_warnings,
                )
                # the draft form must be published with a version after creation if there is no error
                if not draft.get("publishedAt"):
                    versions = odk_service.get_form_versions(odk_project_id, form_id)
                    if versions:
                        max_ver = max(float(v["version"]) for v in versions)
                        next_version = f"{max_ver + 0.1:.1f}"  # e.g. "1.1" → "1.2"
                    else:
                        next_version = "1"
                    odk_service.publish_draft(odk_project_id, form_id, next_version)

                ODKCacheManager.invalidate_project_cache(
                    request.user.id, odk_project_id
                )

                return Response(draft, status=status.HTTP_201_CREATED)

        except ODKValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating/updating draft: {e}")
            return Response(
                {"error": "Unable to create/update draft", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def delete(self, request, project_id, form_id):
        """Delete a draft"""
        try:
            django_project = Projects.objects.get(pkid=project_id)
        except Projects.DoesNotExist:
            return Response(
                {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_project_id = django_project.odk_id
                if not odk_project_id:
                    return Response(
                        {"error": "ODK project not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                odk_service.delete_draft(odk_project_id, form_id)

                ODKCacheManager.invalidate_project_cache(
                    request.user.id, odk_project_id
                )

                return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error deleting draft: {e}")
            return Response(
                {"error": "Unable to delete draft", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # ================================
    # DRAFT PUBLISH, SUBMISSIONS, VERSIONS, XML, TEST
    # ================================


class FormDraftPublishView(APIView):
    """View for publishing a draft"""

    renderer_classes = [GenericJSONRenderer]
    object_label = "draft_form"

    def post(self, request, project_id, form_id):
        """Publish a draft as a form version"""
        try:
            django_project = Projects.objects.get(pkid=project_id)
        except Projects.DoesNotExist:
            return Response(
                {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
            )

        version = request.data.get("version")

        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_project_id = django_project.odk_id
                if not odk_project_id:
                    return Response(
                        {"error": "ODK project not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                odk_service.publish_draft(odk_project_id, form_id, version)

                ODKCacheManager.invalidate_project_cache(
                    request.user.id, odk_project_id
                )

                return Response({"detail": "Form published"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error publishing draft: {e}")
            return Response(
                {"error": "Unable to publish draft", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class FormDraftSubmissionsView(APIView):
    """View for retrieving draft test submissions"""

    renderer_classes = [GenericJSONRenderer]
    object_label = "draft_submissions"

    def get(self, request, project_id, form_id):
        """Retrieve test submissions for a draft"""
        try:
            django_project = Projects.objects.get(pkid=project_id)
        except Projects.DoesNotExist:
            return Response(
                {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_project_id = django_project.odk_id
                if not odk_project_id:
                    return Response(
                        {"error": "ODK project not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                submissions = odk_service.get_draft_submissions(odk_project_id, form_id)

                return Response({"submissions": submissions}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting draft submissions: {e}")
            return Response(
                {"error": "Unable to get draft submissions", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class FormVersionsView(APIView):
    """View for form version management"""

    renderer_classes = [GenericJSONRenderer]
    object_label = "form_versions"

    def get(self, request, project_id, form_id):
        """Retrieve all published versions of a form"""
        try:
            django_project = Projects.objects.get(pkid=project_id)
        except Projects.DoesNotExist:
            return Response(
                {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_project_id = django_project.odk_id
                if not odk_project_id:
                    return Response(
                        {"error": "ODK project not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                versions = odk_service.get_form_versions(odk_project_id, form_id)

                return Response({"results": versions}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting form versions: {e}")
            return Response(
                {"error": "Unable to get form versions", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class FormVersionXMLView(APIView):
    """View for retrieving XML of a specific version"""

    renderer_classes = [GenericJSONRenderer]
    object_label = "form_version_xml"

    def get(self, request, project_id, form_id, version):
        """Retrieve XML for a specific form version"""
        try:
            django_project = Projects.objects.get(pkid=project_id)
        except Projects.DoesNotExist:
            return Response(
                {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_project_id = django_project.odk_id
                if not odk_project_id:
                    return Response(
                        {"error": "ODK project not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                xml_data = odk_service.get_form_version_xml(
                    odk_project_id, form_id, version
                )
                response = HttpResponse(xml_data, content_type="application/xml")
                response["Content-Disposition"] = (
                    f'attachment; filename="{form_id}_v{version}.xml"'
                )
                return response
        except ODKValidationError:
            raise
        except Exception as e:
            logger.error(f"Error getting form version XML: {e}")
            return Response(
                {"error": "Unable to get form version XML", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
