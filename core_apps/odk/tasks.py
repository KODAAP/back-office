import xml.etree.ElementTree as xEt
from io import BytesIO
from logging import getLogger

from django.utils import timezone

from celery import shared_task
from pyxform.xls2xform import convert

from core_apps.odk.services import ODKCentralService

from .models import Export

logger = getLogger(__name__)


@shared_task
def convert_excel_to_xform_task(file_content, file_name):
    try:
        warnings = []
        result = convert(xlsform=BytesIO(file_content), warnings=warnings)
        xform_xml = result.xform
        xEt.fromstring(xform_xml)
        return xform_xml
    except Exception as e:
        raise Exception(f"Failed to convert Excel to XForm: {str(e)}") from e


@shared_task(bind=True, max_retries=5)
def generate_export_task(self, export_id: str):
    # 1. Tentative de récupération de l'objet Export
    try:
        export = Export.objects.get(id=export_id)
    except Export.DoesNotExist as exc:
        # Si l'objet n'existe pas encore (transaction non terminée), on réessaie
        logger.warning(f"Export {export_id} non trouvé, nouvelle tentative...")
        raise self.retry(exc=exc, countdown=2) from exc

    # 2. Exécution du traitement de l'export
    try:
        user = export.created_by
        options = export.options

        with ODKCentralService(user) as service:
            if export.export_type == export.ExportType.EXCEL:
                file_bytes, filename = service.export_smart_excel(
                    export.odk_project_id, export.form_id, **options
                )
            elif export.export_type == export.ExportType.CSV:
                file_bytes = service.zip_submissions(
                    export.odk_project_id, export.form_id
                )
                filename = f"{export.form_id}_submissions.zip"
            elif export.export_type == export.ExportType.ZIP:
                file_bytes, filename = service.export_zip_structured_media_only(
                    export.odk_project_id, export.form_id
                )
            elif export.export_type == export.ExportType.SHP:
                file_bytes, filename = service.export_shapefile(
                    export.odk_project_id, export.form_id
                )
            else:
                raise ValueError(f"Type d'export non supporté: {export.export_type}")

        # Mise à jour de l'objet Export avec les données générées
        export.file_data = file_bytes
        export.file_name = filename
        export.file_size = len(file_bytes)
        export.status = export.Status.READY
        export.completed_at = timezone.now()
        export.save()

        return {"status": "ready"}

    except Exception as exc:
        # Ici on est sûr que 'export' existe car le premier try a réussi
        export.status = export.Status.ERROR
        export.error_message = str(exc)
        export.save()
        logger.error(f"Erreur lors de la génération de l'export {export_id}: {exc}")
        # On réessaie pour les erreurs temporaires (ex: timeout API ODK)
        raise self.retry(exc=exc, countdown=60) from exc
