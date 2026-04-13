import logging
import re

from django.conf import settings

import requests

from .exceptions import ODKValidationError

logger = logging.getLogger(__name__)


class LocalEnketoService:
    """Service pour interagir avec l'instance Enketo locale"""

    def __init__(self):
        self.api_url = getattr(settings, "ENKETO_API_URL", "http://enketo:8005/api/v2")
        self.api_key = getattr(settings, "ENKETO_API_KEY", "")
        self.public_base_url = getattr(
            settings, "ENKETO_PUBLIC_BASE_URL", "http://localhost:8080"
        )
        self.auth = (
            self.api_key,
            "",
        )  # Enketo utilise l'Auth Basic avec la clé API comme nom d'utilisateur

    def _make_request(self, method, endpoint, **kwargs):
        # Enlever le slash initial si présent pour éviter les doubles slashes
        endpoint = endpoint.lstrip("/")
        url = f"{self.api_url}/{endpoint}"

        try:
            logger.debug(f"Appel Enketo API: {method} {url}")
            response = requests.request(method, url, auth=self.auth, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = e.response.text
            logger.error(f"Erreur Enketo API {e.response.status_code}: {error_msg}")
            raise ODKValidationError(
                f"Erreur Enketo: {error_msg}", status_code=e.response.status_code
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à Enketo: {str(e)}")
            raise

    def get_edit_url(self, server_url, form_id, instance_id, return_url=None):
        """
        Génère un lien de modification via l'Enketo local.

        Args:
            server_url (str): URL du serveur ODK Central (ex: https://odk.insuco.net)
            form_id (str): ID XML du formulaire
            instance_id (str): ID de l'instance (soumission) à modifier
            return_url (str, optional): URL de redirection après soumission

        Returns:
            str: URL de modification Enketo accessible par le navigateur
        """
        # S'assurer que server_url ne contient pas /v1 pour Enketo
        if "/v1" in server_url:
            server_url = server_url.split("/v1")[0]

        payload = {
            "server_url": server_url,
            "form_id": form_id,
            "instance_id": instance_id,
        }
        if return_url:
            payload["return_url"] = return_url

        # Note: L'API Enketo attend souvent des paramètres en application/x-www-form-urlencoded
        result = self._make_request("POST", "instance/edit", data=payload)

        edit_url = result.get("url")
        if edit_url:
            # Remplacement de l'hôte interne par l'hôte public
            # Exemple: http://enketo:8005/-/edit/ID -> http://localhost:8080/-/edit/ID
            edit_url = re.sub(r"https?://[^/]+", self.public_base_url, edit_url)

        return edit_url

    def get_survey_url(self, server_url, form_id):
        """
        Récupère l'URL Enketo locale pour une nouvelle saisie.
        """
        if "/v1" in server_url:
            server_url = server_url.split("/v1")[0]

        payload = {
            "server_url": server_url,
            "form_id": form_id,
        }
        result = self._make_request("POST", "survey", data=payload)

        url = result.get("url")
        if url:
            url = re.sub(r"https?://[^/]+", self.public_base_url, url)
        return url
