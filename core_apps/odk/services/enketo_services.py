import logging
import re

from django.conf import settings

import requests

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

    def _clean_server_url(self, server_url: str) -> str:
        """Normalise l'URL ODK Central attendue par Enketo.

        Enketo Express attend généralement l'URL de base d'ODK Central sans le
        suffixe `/v1`. Cette méthode retire ce suffixe lorsqu'il est présent,
        en ciblant uniquement `/v1` en fin d'URL.

        Args:
            server_url (str): URL du serveur ODK Central (ex: `https://odk.exemple.tld/v1`).

        Returns:
            str: URL de base sans `/v1` (ex: `https://odk.exemple.tld`).
        """
        return re.sub(r"/v1/?$", "", server_url.rstrip("/"))

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
        """
        Effectue une requête à l'API Enketo.

        Cette méthode gère l'authentification Basic, le logging et tente une
        alternative d'URL en cas de 404 (pour certaines configurations Enketo Express).

        Args:
            method (str): Méthode HTTP (GET, POST, etc.).
            endpoint (str): Point de terminaison de l'API.
            **kwargs: Arguments supplémentaires pour requests (data, params, headers, etc.).

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
            # Si on envoie des données, on les logge (attention aux données sensibles si nécessaire)
            if kwargs.get("data"):
                logger.debug(f"Payload Enketo: {kwargs.get('data')}")

            # Authentification Basic Auth
            timeout = kwargs.pop("timeout", self.timeout)
            response = requests.request(
                method, url, auth=self.auth, timeout=timeout, **kwargs
            )

            # Log du statut de la réponse
            logger.info(f"Réponse Enketo API [{response.status_code}] sur {url}")

            # Si on a une 404, et que l'URL ne contient pas /-/ alors que base path est -,
            # on tente une alternative (cas spécifique de certaines configs Enketo Express)
            if response.status_code == 404 and "/-/" not in url:
                alt_url = url.replace("/api/v2", "/-/api/v2")
                logger.info(f"404 reçu. Tentative alternative avec /-/ : {alt_url}")
                alt_response = requests.request(
                    method, alt_url, auth=self.auth, timeout=timeout, **kwargs
                )
                if alt_response.status_code < 400:
                    logger.info(f"Succès avec l'URL alternative: {alt_url}")
                    return self._parse_json_response(alt_response, alt_url)

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
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Erreur de connexion à Enketo ({url}): {str(e)}")
            raise ODKValidationError(
                f"Impossible de joindre le serveur Enketo sur {url}. Vérifiez l'hôte et le port."
            )
        except Exception as e:
            logger.error(
                f"Erreur inattendue lors de l'appel à Enketo ({url}): {str(e)}"
            )
            raise

    # def check_connection(self):
    #     """
    #     Vérifie la connexion avec le serveur Enketo.
    #     """
    #     # Construire l'URL de base (peut inclure /-/ selon la config)
    #     base_url = self.api_url
    #     try:
    #         # Test simple: faire un HEAD sur l'URL de base pour vérifier connectivité
    #         response = requests.head(base_url, auth=self.auth, timeout=5, allow_redirects=True)
    #         if response.status_code < 400:
    #             return {
    #                 "success": True,
    #                 "message": "Connexion à Enketo réussie.",
    #                 "data": {"status_code": response.status_code}
    #             }
    #         else:
    #             # Essayer l'URL alternative avec /-/
    #             if "/-/" not in base_url:
    #                 alt_url = base_url.replace("/api/v2", "/-/api/v2")
    #                 alt_response = requests.head(alt_url, auth=self.auth, timeout=5, allow_redirects=True)
    #                 if alt_response.status_code < 400:
    #                     return {
    #                         "success": True,
    #                         "message": "Connexion à Enketo réussie (URL alternative).",
    #                         "data": {"status_code": alt_response.status_code}
    #                     }
    #             return {
    #                 "success": False,
    #                 "message": f"Enketo a répondu avec le statut {response.status_code}",
    #                 "status_code": response.status_code
    #             }
    #     except requests.exceptions.ConnectionError as e:
    #         return {
    #             "success": False,
    #             "message": f"Impossible de joindre Enketo: {str(e)}"
    #         }
    #     except Exception as e:
    #         return {
    #             "success": False,
    #             "message": f"Échec de la connexion réseau à Enketo : {str(e)}"
    #         }

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
            endpoint (str): Point de terminaison de l'API (ex: 'survey', 'instance/edit').
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

        server_url = self._clean_server_url(server_url)
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
        return re.sub(r"https?://[^/]+", self.public_base_url, url)

    def get_edit_link(
        self,
        project_id: int,
        form_id: str,
        instance_id: str,
        local: bool = True,
        return_url: str | None = None,
    ) -> str:
        """Génère un lien de modification Enketo pour une soumission.

        Args:
            project_id (int): Identifiant du projet ODK Central.
            form_id (str): Identifiant XML du formulaire.
            instance_id (str): Identifiant de la soumission.
            local (bool): Si True, utilise l'Enketo local.
            return_url (str | None): URL de redirection.
        """
        if local:
            return self.get_edit_url(
                self.base_url,
                form_id,
                instance_id,
                project_id=project_id,
                return_url=return_url,
            )
        else:
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
        else:
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
        else:
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
