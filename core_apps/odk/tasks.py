import xml.etree.ElementTree as xEt
from io import BytesIO

from django.contrib.auth import get_user_model
from django.utils import timezone

from celery import shared_task
from pyxform.xls2xform import convert

from core_apps.odk.services import ODKCentralService

from .models import Export


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


@shared_task(bind=True, max_retries=3)
def generate_export_task(self, export_id: str):
    User = get_user_model()

    try:
        export = Export.objects.get(id=export_id)
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

        export.file_data = file_bytes
        export.file_name = filename
        export.file_size = len(file_bytes)
        export.status = export.Status.READY
        export.completed_at = timezone.now()
        export.save()

        return {"status": "ready"}

    except Exception as exc:
        export.status = export.Status.ERROR
        export.error_message = str(exc)
        export.save()
        raise self.retry(exc=exc, countdown=60)
