import io
import logging
from io import BytesIO

from django.http import FileResponse, HttpResponse

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core_apps.common.renderers import GenericJSONRenderer
from core_apps.odk.mixins import ProjectValidationMixin
from core_apps.odk.models import Export
from core_apps.odk.services import ODKCentralService
from core_apps.odk.services.exceptions import ODKValidationError
from core_apps.odk.tasks import generate_export_task

logger = logging.getLogger(__name__)


CONTENT_TYPES = {
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
    "zip": "application/zip",
    "shp": "application/zip",
}


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
                    content_type = "text/csv"
                else:
                    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

                file_bytes = odk_service.export_submissions(
                    odk_project_id, form_id, to=to
                )
                response = HttpResponse(
                    file_bytes,
                    content_type=content_type,
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

    @staticmethod
    def clean_odk_keys(obj):
        if isinstance(obj, dict):
            return {
                k: SubmissionsDataView.clean_odk_keys(v)
                for k, v in obj.items()
                if not (k.startswith("@odata") or "@odata" in k)
            }
        elif isinstance(obj, list):
            return [SubmissionsDataView.clean_odk_keys(x) for x in obj]
        else:
            return obj

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

                expand = request.query_params.get("expand", "false").lower() == "true"
                filter_param = request.query_params.get("$filter") or None
                top_param = request.query_params.get("$top")
                skip_param = request.query_params.get("$skip")
                select_param = request.query_params.get("$select") or None

                top = int(top_param) if top_param is not None else None
                skip = int(skip_param) if skip_param is not None else None

                data = SubmissionsDataView.clean_odk_keys(
                    odk_service.submissions_data(
                        odk_id,
                        form_id,
                        expand=expand,
                        filter=filter_param,
                        top=top,
                        skip=skip,
                        select=select_param,
                    )
                )
                return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting submissions data: {e}")
            return Response(
                {"error": "Unable to get submissions data", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SubmissionsZipView(ProjectValidationMixin, APIView):

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
                zip_file = odk_service.zip_submissions(odk_id, form_id)
                response = HttpResponse(zip_file, content_type="application/zip")
                response["Content-Disposition"] = (
                    f'attachment; filename="{form_id}_submissions.zip"'
                )
                return response
        except Exception as e:
            logger.error(f"Error getting submissions data: {e}")
            return Response(
                {"error": "Unable to get submissions data", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class FormRepeatListView(ProjectValidationMixin, APIView):

    def get(self, request, project_id, form_id):
        """Retrieve list of repeats (tables) for a specific form"""
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
                odk_response = odk_service.form_repeat_list(odk_project_id, form_id)

                # Transformation de la réponse
                repeats = []
                # ODK Central renvoie généralement les entités dans la clé 'value'
                raw_repeats = (
                    odk_response.get("value", [])
                    if isinstance(odk_response, dict)
                    else []
                )

                for item in raw_repeats:
                    original_name = item.get("name", "")
                    # Split par le point et garde le dernier élément
                    name_parts = original_name.split(".")
                    display_name = name_parts[-1] if name_parts else original_name

                    repeats.append({"name": display_name, "path": item.get("url")})

                return Response({"repeats": repeats}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting form repeats: {e}")
            return Response(
                {"error": "Unable to get form repeats", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SubmissionSpecificRepeatDataView(ProjectValidationMixin, APIView):

    def get(self, request, project_id, form_id, instance_id, repeat_name):
        """Retrieve repeat data for a specific submission instance"""
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

                # On récupère le path du repeat depuis les query params si présent, sinon le nom
                repeat_path = request.query_params.get("path", repeat_name)

                data = SubmissionsDataView.clean_odk_keys(
                    odk_service.submission_repeat_data(
                        odk_id, form_id, repeat_path, instance_id=instance_id
                    )
                )
                return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting specific repeat data: {e}")
            return Response(
                {"error": "Unable to get repeat data", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SmartExcelExportView(ProjectValidationMixin, APIView):
    """Export intelligent Excel multi-onglets avec labels et nettoyage."""

    def get(self, request, project_id: int, form_id: str):
        django_project, error_response = self.validate_project(project_id)
        if error_response:
            return error_response

        remove_group_prefix_str = request.query_params.get(
            "remove_group_prefix", "true"
        )
        remove_group_prefix = remove_group_prefix_str.lower() == "true"
        include_labels_str = request.query_params.get("include_labels", "true")
        include_labels = include_labels_str.lower() == "true"
        include_choice_labels_str = request.query_params.get(
            "include_choice_labels", "false"
        )
        include_choice_labels = include_choice_labels_str.lower() == "true"
        language = request.query_params.get("language")

        try:
            with ODKCentralService(request.user, request=request) as service:
                file_bytes, filename = service.export_smart_excel(
                    django_project.odk_id,
                    form_id,
                    remove_group_prefix=remove_group_prefix,
                    include_labels=include_labels,
                    include_choice_labels=include_choice_labels,
                    language=language,
                )
            response = FileResponse(
                io.BytesIO(file_bytes),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                filename=filename,
            )
            return response
        except Exception as e:
            logger.error(f"Error generating smart Excel export: {e}")
            return Response(
                {"error": "Unable to generate smart Excel export", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MediaZipExportView(ProjectValidationMixin, APIView):
    """
    Lance un export ZIP structuré (médias uniquement, sans CSV) de façon asynchrone.

    POST /projects/{project_id}/forms/{form_id}/exports/zip-media/
    → Crée un Export de type ZIP, lance la tâche Celery, retourne l'id pour polling.

    Réponse 202 :
        { "id": "<uuid>", "status": "pending" }

    Polling : GET /exports/<id>/status/
    Téléchargement : GET /exports/<id>/download/
    """

    def post(self, request, project_id: int, form_id: str):
        project, error = self.validate_project(project_id)
        if error:
            return error
        odk_project_id, error = self.validate_odk_association(project)
        if error:
            return error

        export = Export.objects.create(
            odk_project_id=odk_project_id,
            form_id=form_id,
            export_type=Export.ExportType.ZIP,
            options={},  # pas d'options pour ce type d'export
            created_by=request.user,
        )

        generate_export_task.delay(str(export.id))

        return Response(
            {"id": str(export.id), "status": export.status},
            status=status.HTTP_202_ACCEPTED,
        )


class ShapefileExportView(ProjectValidationMixin, APIView):
    """
    Lance un export Shapefile (Option 3 : Table / Type de géométrie) de façon asynchrone.

    POST /projects/{project_id}/forms/{form_id}/exports/shapefile/
    → Crée un Export de type SHP, lance la tâche Celery, retourne l'id pour polling.

    Réponse 202 :
        { "id": "<uuid>", "status": "pending" }

    Polling : GET /exports/<id>/status/
    Téléchargement : GET /exports/<id>/download/
    Le fichier téléchargé est un ZIP contenant les dossiers Table/TypeGéom/fichiers.shp
    """

    def post(self, request, project_id: int, form_id: str):
        project, error = self.validate_project(project_id)
        if error:
            return error
        odk_project_id, error = self.validate_odk_association(project)
        if error:
            return error

        export = Export.objects.create(
            odk_project_id=odk_project_id,
            form_id=form_id,
            export_type=Export.ExportType.SHP,
            options={},
            created_by=request.user,
        )

        generate_export_task.delay(str(export.id))

        return Response(
            {"id": str(export.id), "status": export.status},
            status=status.HTTP_202_ACCEPTED,
        )


class GeoJSONUnifiedView(ProjectValidationMixin, APIView):
    """
    Retourne un FeatureCollection GeoJSON unifié (table principale + repeats).
    GET /api/v1/odk/projects/{project_id}/forms/{form_id}/geodata/
    """

    def get(self, request, project_id: int, form_id: str):
        from django.http import JsonResponse

        project, error = self.validate_project(project_id)
        if error:
            return error
        odk_project_id, error = self.validate_odk_association(project)
        if error:
            return error

        try:
            with ODKCentralService(request.user, request=request) as service:
                geojson = service.get_geojson_unified(odk_project_id, form_id)
            return JsonResponse(geojson, status=200)
        except ODKValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"GeoJSONUnifiedView error: {e}")
            return Response(
                {
                    "error": "Impossible de récupérer les données géographiques",
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ExportStatusView(APIView):
    def get(self, request, export_id: str):
        try:
            export = Export.objects.get(id=export_id, created_by=request.user)
        except Export.DoesNotExist:
            return Response(
                {"error": "Export introuvable"}, status=status.HTTP_404_NOT_FOUND
            )

        data = {
            "id": str(export.id),
            "status": export.status,
            "file_name": export.file_name,
            "file_size": export.file_size,
            "error_message": export.error_message if export.status == "error" else None,
            "completed_at": (
                export.completed_at.isoformat() if export.completed_at else None
            ),
        }
        return Response(data)


class ExportDownloadView(APIView):
    def get(self, request, export_id: str):
        try:
            export = Export.objects.get(
                id=export_id, created_by=request.user, status=Export.Status.READY
            )
        except Export.DoesNotExist:
            return Response(
                {"error": "Export prêt introuvable"}, status=status.HTTP_404_NOT_FOUND
            )

        content_type = CONTENT_TYPES.get(export.export_type, "application/octet-stream")

        response = FileResponse(
            BytesIO(export.file_data),
            content_type=content_type,
            as_attachment=True,
            filename=export.file_name,
        )
        return response


class ExportListCreateView(ProjectValidationMixin, APIView):
    """Gestion des exports : liste et création asynchrone."""

    def get(self, request, project_id: int, form_id: str):
        project, error = self.validate_project(project_id)
        if error:
            return error
        odk_project_id, error = self.validate_odk_association(project)
        if error:
            return error

        exports = Export.objects.filter(
            odk_project_id=odk_project_id, form_id=form_id, created_by=request.user
        ).order_by("-created_at")

        data = [
            {
                "id": str(e.id),
                "export_type": e.export_type,
                "status": e.status,
                "file_name": e.file_name,
                "file_size": e.file_size,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "error_message": e.error_message if e.status == "error" else None,
            }
            for e in exports
        ]
        return Response(data)

    def post(self, request, project_id: int, form_id: str):
        project, error = self.validate_project(project_id)
        if error:
            return error
        odk_project_id, error = self.validate_odk_association(project)
        if error:
            return error

        export_type = request.data.get("export_type", "excel")
        options = request.data.get("options", {})

        export = Export.objects.create(
            odk_project_id=odk_project_id,
            form_id=form_id,
            export_type=export_type,
            options=options,
            created_by=request.user,
        )

        generate_export_task.delay(str(export.id))

        return Response(
            {
                "id": str(export.id),
                "status": export.status,
            },
            status=status.HTTP_202_ACCEPTED,
        )
