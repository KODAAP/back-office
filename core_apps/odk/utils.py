import base64
import json
import logging
import os
import zlib
from io import BytesIO

import requests
import segno
from dotenv import load_dotenv
from urllib3.exceptions import InsecureRequestWarning

from config.env import CUR_ENV_FILE

logger = logging.getLogger(__name__)

if os.path.isfile(CUR_ENV_FILE):
    load_dotenv(CUR_ENV_FILE)


def get_ssl_verify():
    """
    Determine if SSL verification should be used for ODK requests.
    For development environments, this can be disabled via an environment variable.
    """
    verify_ssl = os.getenv("ODK_VERIFY_SSL", "True").lower() in ("true", "1", "t")

    if not verify_ssl:
        # Suppress only the single warning from urllib3 needed.
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
        logger.warning(
            "SSL verification is disabled for ODK Central API calls. This should not be used in production."
        )

    return verify_ssl


def generate_odk_qr_code(server_url, app_user_token, project_id, project_name):
    """Génère un QR code pour la configuration ODK Collect"""
    # Préparation des données à encoder
    settings = {
        "general": {
            "server_url": f"{server_url}/v1/key/{app_user_token}/projects/{project_id}"
        },
        "admin": {},
        "project": {"name": project_name},
    }
    compressed = zlib.compress(json.dumps(settings).encode("utf-8"))
    qr_data = base64.b64encode(compressed)

    # Génération du QR code
    qr = segno.make(qr_data, micro=False)
    buffer = BytesIO()
    qr.save(buffer, kind="png", scale=4)
    buffer.seek(0)

    # Encodage base64 pour affichage web
    img_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    return img_base64
