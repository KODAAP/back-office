import logging

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class ODKCacheManager:
    """Gestionnaire de cache pour les données ODK"""

    # Préfixe pour toutes les clés de cache ODK
    CACHE_PREFIX = "odk_"
    # Durées de cache par défaut (en secondes)
    DEFAULT_TIMEOUT = 300  # 5 minutes
    PROJECTS_TIMEOUT = 600  # 10 minutes
    FORMS_TIMEOUT = 300  # 5 minutes
    SUBMISSIONS_TIMEOUT = 60  # 1 minute

    @staticmethod
    def get_cache_key(user_id: int, resource_type: str, resource_id: str = None) -> str:
        """Génère une clé de cache unique"""
        key_parts = [ODKCacheManager.CACHE_PREFIX, resource_type, str(user_id)]
        if resource_id:
            key_parts.append(str(resource_id))
        return "_".join(key_parts)

    @staticmethod
    def cache_user_projects(user_id: int, projects, timeout: int = None) -> None:
        """Met en cache les projets d'un utilisateur"""
        cache_key = ODKCacheManager.get_cache_key(user_id, "projects")
        cache_data = {"projects": projects, "cached_at": timezone.now().isoformat()}

        if timeout is None:
            timeout = ODKCacheManager.PROJECTS_TIMEOUT

        cache.set(cache_key, cache_data, timeout)
        logger.debug(
            f"Projets ODK mis en cache pour l'utilisateur {user_id} (expire dans {timeout}s)"
        )

    @staticmethod
    def get_cached_user_projects(user_id: int):
        """Récupère les projets en cache"""
        cache_key = ODKCacheManager.get_cache_key(user_id, "projects")
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.debug(f"Projets ODK récupérés du cache pour l'utilisateur {user_id}")
            return cached_data["projects"]

        logger.debug(f"Aucun projet ODK en cache pour l'utilisateur {user_id}")
        return None

    @staticmethod
    def cache_project_forms(
        user_id: int, project_id: int | str, forms: list, timeout: int = None
    ) -> None:
        """Met en cache les formulaires d'un projet"""
        cache_key = ODKCacheManager.get_cache_key(user_id, "forms", project_id)
        cache_data = {"forms": forms, "cached_at": timezone.now().isoformat()}

        if timeout is None:
            timeout = ODKCacheManager.FORMS_TIMEOUT

        cache.set(cache_key, cache_data, timeout)
        logger.debug(
            f"Formulaires ODK mis en cache pour l'utilisateur {user_id}, projet {project_id} (expire dans {timeout}s)"
        )

    @staticmethod
    def get_cached_project_forms(user_id: int, project_id: int | str):
        """Récupère les formulaires en cache"""
        cache_key = ODKCacheManager.get_cache_key(user_id, "forms", project_id)
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.debug(
                f"Formulaires ODK récupérés du cache pour l'utilisateur {user_id}, projet {project_id}"
            )
            return cached_data["forms"]

        logger.debug(
            f"Aucun formulaire ODK en cache pour l'utilisateur {user_id}, projet {project_id}"
        )
        return None

    @staticmethod
    def cache_form_submissions(
        user_id: int,
        project_id: int,
        form_id: str,
        submissions: list,
        timeout: int = None,
    ) -> None:
        """Met en cache les soumissions d'un formulaire"""
        cache_key = ODKCacheManager.get_cache_key(
            user_id, "submissions", f"{project_id}/{form_id}"
        )
        cache_data = {
            "submissions": submissions,
            "cached_at": timezone.now().isoformat(),
        }

        if timeout is None:
            timeout = ODKCacheManager.SUBMISSIONS_TIMEOUT

        cache.set(cache_key, cache_data, timeout)
        logger.debug(
            f"Soumissions ODK mises en cache pour l'utilisateur {user_id}, formulaire {form_id} (expire dans {timeout}s)"
        )

    @staticmethod
    def get_cached_form_submissions(user_id: int, project_id: int, form_id: str):
        """Récupère les soumissions en cache"""
        cache_key = ODKCacheManager.get_cache_key(
            user_id, "submissions", f"{project_id}/{form_id}"
        )
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.debug(
                f"Soumissions ODK récupérées du cache pour l'utilisateur {user_id}, formulaire {form_id}"
            )
            return cached_data["submissions"]

        logger.debug(
            f"Aucune soumission ODK en cache pour l'utilisateur {user_id}, formulaire {form_id}"
        )
        return None

    @staticmethod
    def invalidate_user_cache(user_id: int) -> None:
        """Invalide tout le cache d'un utilisateur"""
        # Supprimer la liste des projets
        projects_key = ODKCacheManager.get_cache_key(user_id, "projects")
        cache.delete(projects_key)

        logger.info(f"Cache ODK invalidé pour l'utilisateur {user_id}")

    @staticmethod
    def invalidate_project_cache(user_id: int, project_id: int | str) -> None:
        """Invalide le cache d'un projet spécifique"""
        # Clé pour les formulaires du projet
        forms_key = ODKCacheManager.get_cache_key(user_id, "forms", project_id)
        cache.delete(forms_key)

        # Invalide également la liste des projets
        projects_key = ODKCacheManager.get_cache_key(user_id, "projects")
        cache.delete(projects_key)

        logger.info(
            f"Cache du projet ODK {project_id} invalidé pour l'utilisateur {user_id}"
        )
