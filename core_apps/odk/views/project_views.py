import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core_apps.common.renderers import GenericJSONRenderer
from core_apps.odk.services import ODKCentralService

from ..cache import ODKCacheManager

logger = logging.getLogger(__name__)


class ODKProjectListView(APIView):
    renderer_classes = [GenericJSONRenderer]
    object_label = "odkProjects"

    def get(self, request):
        if cached_projects := ODKCacheManager.get_cached_user_projects(request.user.id):
            # Retourne les données en cache
            return Response(
                {
                    "count": len(cached_projects),
                    "results": cached_projects,
                    "cached": True,
                    "userRole": request.user.profile.get_odk_role_display(),
                },
                status=status.HTTP_200_OK,
            )

        # Sinon, récupère depuis ODK avec le pool de comptes
        try:
            with ODKCentralService(request.user, request=request) as odk_service:
                projects = odk_service.get_projects()

                # Met en cache le résultat
                ODKCacheManager.cache_user_projects(request.user.id, projects)

                return Response(
                    {
                        "count": len(projects),
                        "results": projects,
                        "cached": False,
                        "userRole": request.user.profile.get_odk_role_display(),
                    },
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des projets ODK: {e}")
            return Response(
                {"error": "Impossible de récupérer les projets", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
