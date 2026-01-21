import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core_apps.common.renderers import GenericJSONRenderer
from core_apps.odk.mixins import ProjectValidationMixin
from core_apps.odk.serializers import PublicLinkCreateSerializer
from core_apps.odk.services import ODKCentralService

logger = logging.getLogger(__name__)


class CreateListAccessView(ProjectValidationMixin, APIView):
    """Handles creation and listing of public access links for ODK forms"""

    renderer_classes = [
        GenericJSONRenderer,
    ]

    @property
    def object_label(self):
        return "public_links" if self.request.method == "GET" else "public_link"

    def get(self, request, project_id, form_id):
        """List all public access links for a specific form"""
        project, error_response = self.validate_project(project_id)
        if error_response:
            return error_response

        extended = request.GET.get("extended", "false").lower() == "true"

        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_project_id = project.odk_id
                if not odk_project_id:
                    return Response(
                        {"error": "Project is not associated with ODK"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                access_links = odk_service.list_public_links(
                    odk_project_id, form_id, extended
                )
                return Response(
                    {"count": len(access_links), "results": access_links},
                    status=status.HTTP_200_OK,
                )
        except Exception as e:
            logger.error(f"Error getting form access links: {e}")
            return Response(
                {"error": "Unable to get form access links", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request, project_id, form_id):
        """Create a new public access link for a specific form"""
        project, error_response = self.validate_project(project_id)
        if error_response:
            return error_response

        serializer = PublicLinkCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        display_name = serializer.validated_data["display_name"]
        once = serializer.validated_data.get("once", False)
        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_project_id = project.odk_id
                if not odk_project_id:
                    return Response(
                        {"error": "Project is not associated with ODK"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                access_link = odk_service.create_public_link(
                    odk_project_id, form_id, display_name, once
                )
                return Response(access_link, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating form access link: {e}")
            return Response(
                {"error": "Unable to create form access link", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RevokeAccessLinkView(APIView):
    """Handles revocation of a specific public access link for ODK forms"""

    def delete(self, request, token):
        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                odk_service.revoke_public_link(token)
                return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting form access link: {e}")
            return Response(
                {"error": "Unable to delete form access link", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
