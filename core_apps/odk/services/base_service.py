import json
import logging
import os
import tempfile
import threading
import time
from datetime import timedelta
from typing import Any, Dict, Optional

from django.conf import settings
from django.utils import timezone

import pyxform.xls2json
import requests

from core_apps.common.utils import log_audit_action
from core_apps.odk.models import ODKUserSessions
from core_apps.odk.utils import get_ssl_verify

from .exceptions import ODKValidationError
from .pool_services import ODKAccountPool

logger = logging.getLogger(__name__)


# Ce service de base est le cerveau pour communiquer avec l'API ODK Central.
# Il gère un pool de comptes ODK pour éviter de surcharger l'API avec des demandes d'authentification.
# Il est conçu pour être utilisé comme un gestionnaire de contexte (avec `with`), ce qui
# garantit qu'un compte ODK est emprunté du pool au début d'une opération et
# retourné proprement à la fin, même en cas d'erreur.
class BaseODKService:
    """Base service for interacting with the ODK Central API"""

    def __init__(self, django_user, request=None):
        """
        Initialise le service.

        Args:
            django_user: L'utilisateur Django qui effectue l'action.
                         C'est crucial pour l'audit et la gestion des sessions.
            request: L'objet requête Django, optionnel mais utile pour le logging.
        """
        self.django_user = django_user
        self.request = request
        self.base_url = getattr(
            settings, "ODK_CENTRAL_URL", "https://odk.insuco.net/v1"
        )

        # Ces attributs sont gérés par le gestionnaire de contexte (`with`).
        self.current_account = None
        self.current_session_data = None

        # Le pool qui gère la disponibilité des comptes ODK.
        self.odk_account_pool = ODKAccountPool()

    def __enter__(self):
        """
        Début du contexte : on emprunte un compte ODK au pool.
        C'est ici que la magie opère pour le multithreading : chaque `with`
        obtient un compte disponible, ce qui évite les conflits.
        """
        self.current_account = self.odk_account_pool.get_account()
        self.current_session_data = self.odk_account_pool.get_session_for_account(
            self.current_account
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Fin du contexte : on remet le compte dans le pool pour qu'il soit
        disponible pour une autre opération.
        """
        if self.current_account:
            self.odk_account_pool.return_account(self.current_account)

    def _get_or_create_token(self) -> str:
        """
        Récupère un token ODK valide pour le compte courant.
        Si le token en mémoire est encore bon, on le réutilise. Sinon, on s'authentifie
        auprès d'ODK pour en obtenir un nouveau.
        """
        if not self.current_account:
            raise Exception("Aucun compte ODK n'est assigné à ce service.")

        session_data = self.current_session_data
        account = self.current_account

        # 1. Vérifier si on a déjà un token valide en mémoire.
        if (
            session_data.get("token")
            and session_data.get("expires_at")
            and timezone.now() < session_data["expires_at"]
        ):
            return session_data["token"]

        # 2. Si non, on doit s'authentifier pour en créer un nouveau.
        try:
            response = session_data["session"].post(
                f"{self.base_url}/sessions",
                json={"email": account["email"], "password": account["password"]},
                verify=get_ssl_verify(),
            )
            response.raise_for_status()  # Lève une exception si le statut est 4xx ou 5xx.

            token = response.json().get("token")
            # On met une expiration à 23h pour avoir une marge de sécurité
            # et forcer le renouvellement avant l'expiration réelle côté ODK.
            expires_at = timezone.now() + timedelta(hours=23)

            # 3. Mettre à jour les données de session en mémoire pour les futurs appels.
            session_data["token"] = token
            session_data["expires_at"] = expires_at
            session_data["session"].headers.update(
                {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            )

            # 4. Sauvegarder aussi le token en base de données pour l'utilisateur Django.
            #    Ça peut être utile pour du débogage ou d'autres mécanismes.
            thread_id = threading.current_thread().ident
            ODKUserSessions.objects.update_or_create(
                user=self.django_user,
                defaults={
                    "odk_token": token,
                    "token_expired_at": expires_at,
                    "actor_id": account["id"],
                },
            )

            logger.info(
                f"Authentification ODK réussie pour le compte {account['id']} (thread: {thread_id})"
            )
            return token

        except Exception as e:
            thread_id = threading.current_thread().ident
            logger.error(
                f"Échec de l'authentification ODK pour le compte {account['id']}: {e} (thread: {thread_id})"
            )
            # On propage l'erreur pour que la méthode appelante puisse la gérer.
            raise

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Effectue une requête vers l'API ODK Central.
        Cette méthode est le cœur de la communication : elle gère les tokens,
        les tentatives multiples (retry) et les erreurs de manière robuste.
        """
        # On récupère les réglages depuis les settings de Django, avec des valeurs par défaut.
        max_retries = getattr(settings, "ODK_MAX_RETRIES", 5)
        timeout = getattr(settings, "ODK_REQUEST_TIMEOUT", 120)

        # Permet à l'appelant de spécifier s'il attend du JSON ou du contenu brut (ex: un fichier CSV).
        return_json = kwargs.pop("return_json", True)

        # Ajout des valeurs par défaut si non spécifiées par l'appelant.
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout
        if "verify" not in kwargs:
            kwargs["verify"] = get_ssl_verify()

        # Boucle de tentatives multiples
        for attempt in range(max_retries):
            try:
                # S'assure qu'on a un token valide avant chaque requête.
                self._get_or_create_token()
                session = self.current_session_data["session"]

                logger.debug(
                    f"Tentative {attempt + 1}/{max_retries} - {method} {self.base_url}/{endpoint}"
                )

                response = session.request(
                    method, f"{self.base_url}/{endpoint}", **kwargs
                )
                response.raise_for_status()  # Le point central pour la gestion des erreurs HTTP.

                # Si la requête réussit mais ne retourne aucun contenu (ex: DELETE),
                # on renvoie une réponse de succès standard.
                if response.status_code == 204 or not response.content:
                    return {"success": True, "status_code": response.status_code}

                # Si l'appelant veut le contenu brut, on le lui donne.
                # Sinon, on décode le JSON.
                return response.json() if return_json else response.content

            # --- Gestion des erreurs spécifiques ---

            except requests.exceptions.ConnectionError as e:
                logger.error(
                    f"Erreur de connexion à ODK Central ({self.base_url}): {e}"
                )
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Attente de 1, 2, 4, 8... secondes.
                    logger.info(f"Nouvelle tentative dans {wait_time} secondes...")
                    time.sleep(wait_time)
                    continue
                # Après la dernière tentative, on lève une exception claire.
                raise Exception(
                    f"Impossible de se connecter au serveur ODK Central. "
                    f"Veuillez vérifier que l'URL '{self.base_url}' est correcte et que le serveur est accessible."
                ) from e

            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout lors de la connexion à ODK Central: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.info(f"Nouvelle tentative dans {wait_time} secondes...")
                    time.sleep(wait_time)
                    continue
                raise Exception(
                    f"Le serveur ODK Central ne répond pas dans le délai imparti ({timeout}s). "
                    f"Veuillez vérifier l'état du serveur ou augmenter la valeur de ODK_REQUEST_TIMEOUT."
                ) from e

            except requests.exceptions.HTTPError as e:
                # Cas spécial : token expiré.
                if e.response.status_code == 401:
                    logger.warning(
                        f"Token expiré pour le compte {self.current_account['id']}, tentative de rafraîchissement..."
                    )
                    # On invalide le token en mémoire pour forcer son renouvellement à la prochaine tentative.
                    self.current_session_data["token"] = None
                    if attempt < max_retries - 1:
                        continue  # On ré-essaie immédiatement.

                status_code = e.response.status_code

                # On essaie d'extraire un message d'erreur plus parlant de la réponse ODK.
                error_detail = None
                try:
                    if e.response.content:
                        error_response = e.response.json()
                        error_detail = error_response
                except (json.JSONDecodeError, ValueError):
                    # Si la réponse n'est pas du JSON, on prend le texte brut.
                    error_detail = e.response.text if e.response.text else str(e)

                logger.error(
                    f"Erreur HTTP {status_code} lors de la requête vers ODK Central: {e}"
                )

                # Erreurs non récupérables, on arrête tout de suite.
                if status_code == 404:
                    raise Exception(f"Ressource non trouvée: {endpoint}") from e
                elif status_code == 403:
                    raise Exception(f"Accès refusé à la ressource: {endpoint}") from e
                # Erreur serveur (5xx), on peut réessayer.
                elif status_code >= 500:
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt
                        logger.info(
                            f"Erreur serveur, nouvelle tentative dans {wait_time} secondes..."
                        )
                        time.sleep(wait_time)
                        continue
                    raise Exception(
                        f"Erreur serveur ODK Central ({status_code}). Veuillez réessayer plus tard."
                    ) from None

                # Pour les autres erreurs 4xx (ex: 400 Bad Request), on lève une exception
                # personnalisée qui contient les détails de l'erreur ODK.
                raise ODKValidationError(
                    str(e), error_detail=error_detail, status_code=status_code
                ) from e

            except json.JSONDecodeError as e:
                logger.error(f"Erreur de décodage JSON: {e}")
                raise Exception(
                    "Le serveur ODK Central a retourné une réponse invalide."
                ) from e

            except Exception as e:
                logger.error(
                    f"Erreur inattendue lors de la requête vers ODK Central: {e}"
                )
                # C'est un joker pour toute autre erreur, on ré-essaie au cas où.
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.info(f"Nouvelle tentative dans {wait_time} secondes...")
                    time.sleep(wait_time)
                    continue
                raise

        # Si on sort de la boucle sans succès.
        raise Exception(
            f"Nombre maximum de tentatives dépassé pour {method} {endpoint}"
        )

    def _log_action(
            self,
            action: str,
            resource_type: str,
            resource_id: str | int,
            details: dict,
            success: bool = True,
    ) -> None:
        """
        Journalise une action dans le journal d'audit.
        Utilise une fonction partagée pour centraliser le logging.
        """
        log_audit_action(
            user=self.django_user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            success=success,
            request=self.request,
        )

    def _get_form_xlsx(self, project_id: int, form_id: str) -> bytes:
        """Télécharge le fichier XLSX du formulaire depuis ODK Central."""
        return self._make_request(
            "GET",
            f"projects/{project_id}/forms/{form_id}.xlsx",
            return_json=False,
        )

    def _get_field_info(self, project_id: int, form_id: str) -> Dict[str, Dict[str, str]]:
        """
        Parse le XLSForm pour extraire le type et le label de chaque champ.
        Retourne un dict: field_path -> {"type": "...", "label": "..."}
        """
        xlsx_bytes = self._get_form_xlsx(project_id, form_id)
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(xlsx_bytes)
            tmp_path = tmp.name
        try:
            survey = pyxform.xls2json.parse_file_to_json(tmp_path)
        finally:
            os.unlink(tmp_path)

        field_info: Dict[str, Dict[str, str]] = {}

        def _extract_label(node_label, name: str) -> str:
            if not node_label:
                return name
            if isinstance(node_label, list) and node_label:
                # On prend le premier label par défaut (souvent fr ou en)
                return node_label[0].get("#text", name)
            if isinstance(node_label, dict):
                return node_label.get("#text", name)
            return str(node_label)

        def recurse(node: Any, path: str = "") -> None:
            node_type = node.get("type")
            name = node.get("name", "")
            full_path = f"{path}/{name}" if path and name else name
            
            label = _extract_label(node.get("label"), name)

            if node_type and node_type != "survey" and name:
                info = {"type": node_type, "label": label}
                field_info[full_path] = info
                field_info[name] = info

            # Recurse into groups/repeats
            for child in node.get("children", []):
                recurse(child, full_path)

        recurse(survey)
        return field_info
