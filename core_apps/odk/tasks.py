import xml.etree.ElementTree as xEt
from io import BytesIO

from celery import shared_task
from pyxform.xls2xform import convert


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
