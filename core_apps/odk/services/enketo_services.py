import logging
import re

from django.conf import settings

import requests

from core_apps.odk.models import ODKUserSessions

from .base_service import BaseODKService
from .exceptions import ODKValidationError

logger = logging.getLogger(__name__)


class EnketoService(BaseODKService):
    """Service pour interagir avec Enketo (local ou via ODK Central)."""

    def __init__(self, django_user=None, request=None):
        """Initialise une instance de EnketoService.

        Configure l'URL de l'API Enketo, la clé d'authentification et l'URL
        publique de base. Valide que les settings requis sont présents.

        Args:
            django_user: Utilisateur Django courant.
            request: Requête HTTP Django/DRF.

        Raises:
            ODKValidationError: Si ENKETO_API_URL ou ENKETO_API_KEY ne sont
                pas définis dans les settings Django.
        """
        super().__init__(django_user, request=request)
        self.api_url = getattr(settings, "ENKETO_API_URL", None)
        self.api_key = getattr(settings, "ENKETO_API_KEY", None)
        if not self.api_url or not self.api_key:
            raise ODKValidationError(
                "Configuration Enketo manquante : ENKETO_API_URL et ENKETO_API_KEY sont requis."
            )
        self.public_base_url = getattr(
            settings, "ENKETO_PUBLIC_BASE_URL", "http://localhost:8080"
        )
        self.timeout = getattr(settings, "ENKETO_TIMEOUT", 30)
        # Authentification Basic Auth avec l'API key comme username
        # Enketo Express attend: Authorization: Basic base64(api_key:)
        self.auth = (self.api_key, "")

    def _is_json_response(self, response):
        """Vérifie si la réponse est du JSON valide."""
        content_type = response.headers.get("Content-Type", "")
        return "application/json" in content_type

    def _parse_json_response(self, response, url):
        """Parse la réponse JSON ou lève une erreur appropriée."""
        if not response.content:
            return {}
        if not self._is_json_response(response):
            logger.error(
                f"Réponse non-JSON reçue de {url}: Content-Type={response.headers.get('Content-Type')}"
            )
            raise ODKValidationError(
                f"L'API Enketo a retourné une réponse non-JSON (status {response.status_code}). "
                f"Vérifiez l'URL de l'API. URL: {url}"
            )
        return response.json()

    def _make_enketo_request(self, method, endpoint, **kwargs):
        """Effectue une requête à l'API Enketo.

        Cette méthode gère l'authentification Basic, le logging et tente une
        alternative d'URL en cas de 404 (pour certaines configurations Enketo
        Express).

        Args:
            method (str): Méthode HTTP (GET, POST, etc.).
            endpoint (str): Point de terminaison de l'API.
            **kwargs: Arguments supplémentaires pour requests (data, params,
              headers, etc.).

        Returns:
            dict: Réponse de l'API Enketo désérialisée (JSON).

        Raises:
            ODKValidationError: Si l'API retourne une erreur 4xx ou 5xx.
            Exception: Pour d'autres erreurs réseau ou système.
        """
        # Enlever le slash initial si présent pour éviter les doubles slashes
        endpoint = endpoint.lstrip("/")
        url = f"{self.api_url}/{endpoint}"
        logger.info(f"Tentative Enketo API: {method} {url}")

        try:
            # Si on envoie des données, on les logge
            if kwargs.get("data"):
                logger.debug(f"Payload Enketo: {kwargs.get('data')}")

            # Authentification Basic Auth
            timeout = kwargs.pop("timeout", self.timeout)
            response = requests.request(
                method, url, auth=self.auth, timeout=timeout, **kwargs
            )

            # Log du statut de la réponse
            logger.info(f"Réponse Enketo API [{response.status_code}] sur {url}")

            # Analyse de la réponse en cas d'erreur
            if response.status_code >= 400:
                error_content = response.text
                try:
                    # Tenter de parser le JSON d'erreur si disponible
                    error_json = response.json()
                    error_msg = error_json.get("message", error_content)
                except Exception:
                    error_msg = error_content

                logger.error(
                    f"Erreur Enketo API {response.status_code} sur {url}: {error_msg}"
                )
                raise ODKValidationError(
                    f"Erreur Enketo ({response.status_code}): {error_msg}",
                    status_code=response.status_code,
                )

            # Parser la réponse JSON
            return self._parse_json_response(response, url)
        except requests.exceptions.HTTPError as e:
            # Déjà géré au-dessus, mais au cas où raise_for_status est utilisé ailleurs
            error_msg = e.response.text
            logger.error(
                f"HTTPError Enketo {e.response.status_code} sur {url}: {error_msg}"
            )
            raise ODKValidationError(
                f"Erreur Enketo sur {url}: {error_msg}",
                status_code=e.response.status_code,
            ) from e
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Erreur de connexion à Enketo ({url}): {str(e)}")
            raise ODKValidationError(
                f"Impossible de joindre le serveur Enketo sur {url}. Vérifiez l'hôte et le port."
            ) from e
        except Exception as e:
            logger.error(
                f"Erreur inattendue lors de l'appel à Enketo ({url}): {str(e)}"
            )
            raise

    def _get_enketo_url(
        self,
        endpoint: str,
        server_url: str,
        form_id: str,
        instance_id: str | None = None,
        project_id: int | None = None,
        return_url: str | None = None,
    ) -> str:
        """Méthode générique pour récupérer une URL Enketo via l'API.

        Args:
            endpoint (str): Point de terminaison de l'API (ex: 'survey',
              'instance/edit').
            server_url (str): URL du serveur ODK Central.
            form_id (str): Identifiant XML du formulaire.
            instance_id (str | None): Identifiant de la soumission.
            project_id (int | None): Identifiant du projet.
            return_url (str | None): URL de retour.

        Returns:
            str: URL Enketo publique.
        """
        if not server_url or not server_url.strip():
            raise ODKValidationError(
                "Le paramètre 'server_url' est requis et ne peut pas être vide."
            )
        if not form_id or not form_id.strip():
            raise ODKValidationError(
                "Le paramètre 'form_id' est requis et ne peut pas être vide."
            )
        payload = {"server_url": server_url, "form_id": form_id}

        if instance_id:
            payload["instance_id"] = instance_id
        if project_id is not None:
            payload["project_id"] = str(project_id)
        if return_url:
            payload["return_url"] = return_url

        result = self._make_enketo_request("POST", endpoint, data=payload)
        url = result.get("url")

        if not url:
            logger.error(
                f"L'API Enketo n'a pas retourné d'URL pour {endpoint}. Réponse: {result}"
            )
            raise ODKValidationError(
                f"L'API Enketo n'a pas retourné d'URL pour {endpoint}."
            )

        # Remplacement de l'hôte interne par l'hôte public
        url = re.sub(r"https?://[^/]+", self.public_base_url, url)

        # Injection du token de session ODK pour éviter la ré-authentification.
        url = self._append_session_token(url)

        return url

    def _append_session_token(self, url: str) -> str:
        """Ajoute le token de session ODK à l'URL Enketo.

        Récupère le token Bearer stocké dans ODKUserSessions pour l'utilisateur
        Django courant et l'ajoute en paramètre `st`.
        """
        if not self.django_user:
            return url

        try:
            session = ODKUserSessions.objects.get(user=self.django_user)
            if not session.is_valid():
                logger.warning(
                    "Token ODK expiré pour l'utilisateur %s", self.django_user
                )
                return url

            separator = "&" if "?" in url else "?"
            return f"{url}{separator}st={session.odk_token}"

        except ODKUserSessions.DoesNotExist:
            logger.warning("Pas de session ODK pour l'utilisateur %s", self.django_user)
            return url

    def get_edit_link(
        self,
        project_id: int,
        form_id: str,
        instance_id: str,
        local: bool = True,
        return_url: str | None = None,
    ) -> str:
        """Génère un lien de modification Enketo pour une soumission."""
        if local:
            return self.get_edit_url(
                self.base_url,
                form_id,
                instance_id,
                project_id=project_id,
                return_url=return_url,
            )

        result = self._make_request(
            "POST",
            f"projects/{project_id}/forms/{form_id}/submissions/{instance_id}/edit",
        )
        url = result.get("url")
        if not url:
            raise ODKValidationError(
                f"ODK Central n'a pas retourné d'URL d'édition pour la soumission {instance_id}."
            )
        return url

    def get_survey_link(
        self,
        project_id: int,
        form_id: str,
        local: bool = True,
        return_url: str | None = None,
    ) -> str:
        """Génère un lien Enketo de saisie pour un formulaire."""
        if local:
            return self.get_survey_url(
                self.base_url,
                form_id,
                project_id=project_id,
                return_url=return_url,
            )

        result = self._make_request(
            "POST",
            f"projects/{project_id}/forms/{form_id}/survey",
        )
        url = result.get("url")
        if not url:
            raise ODKValidationError(
                f"ODK Central n'a pas retourné d'URL de saisie pour le formulaire {form_id}."
            )
        return url

    def get_preview_link(
        self,
        project_id: int,
        form_id: str,
        local: bool = True,
    ) -> str:
        """Génère un lien Enketo de prévisualisation pour un formulaire."""
        if local:
            return self.get_preview_url(
                self.base_url,
                form_id,
                project_id=project_id,
            )

        result = self._make_request(
            "POST",
            f"projects/{project_id}/forms/{form_id}/preview",
        )
        url = result.get("url")
        if not url:
            raise ODKValidationError(
                f"ODK Central n'a pas retourné d'URL de prévisualisation pour le formulaire {form_id}."
            )
        return url

    def get_edit_url(
        self,
        server_url: str,
        form_id: str,
        instance_id: str,
        project_id: int | None = None,
        return_url: str | None = None,
    ) -> str:
        """Récupère l'URL Enketo locale pour modifier une soumission."""
        return self._get_enketo_url(
            "instance/edit",
            server_url,
            form_id,
            instance_id=instance_id,
            project_id=project_id,
            return_url=return_url,
        )

    def get_survey_url(
        self,
        server_url: str,
        form_id: str,
        project_id: int | None = None,
        return_url: str | None = None,
    ) -> str:
        """Récupère l'URL Enketo locale pour une nouvelle saisie."""
        return self._get_enketo_url(
            "survey",
            server_url,
            form_id,
            project_id=project_id,
            return_url=return_url,
        )

    def get_preview_url(
        self,
        server_url: str,
        form_id: str,
        project_id: int | None = None,
    ) -> str:
        """Récupère l'URL Enketo de prévisualisation d'un formulaire."""
        return self._get_enketo_url(
            "survey/preview", server_url, form_id, project_id=project_id
        )
