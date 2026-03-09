from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from guardian.shortcuts import assign_perm, get_users_with_perms, remove_perm

from core_apps.common.permissions_config import (
    ADMIN_ROLES,
    PERMISSION_SETS,
    ROLE_ALLOWED_LEVELS,
)
from core_apps.profiles.models import Profile
from core_apps.projects.models import Projects

User = get_user_model()


def can_assign_project_permissions(actor, project) -> bool:
    # Bypass rôles admin/manager
    role = getattr(getattr(actor, "profile", None), "odk_role", None)
    if role in ADMIN_ROLES:
        return True
    # Permission objet OU permission modèle (globale) `manage_project`
    return actor.has_perm("projects.manage_project", project) or actor.has_perm(
        "projects.manage_project"
    )


def assign_project_permission(user, project, permission_level):
    """
    Assigner des permissions à un utilisateur pour un projet spécifique.

    Args:
        user: Instance de User
        project: Instance de Projects
        permission_level: 'read', 'submit', 'contribute', 'manage'
    """
    try:
        user_role = user.profile.odk_role
    except Profile.DoesNotExist:
        raise ValueError(f"User {user.username} does not have a profile.") from None

    # Les administrateurs et managers ont un accès global
    if user_role in ADMIN_ROLES:
        return True

    # Vérifier si le rôle peut avoir ce niveau de permission
    if permission_level not in ROLE_ALLOWED_LEVELS.get(user_role, []):
        raise PermissionDenied(
            f"User with role '{user_role}' cannot be assigned '{permission_level}' permission."
        )

    # Vérifier que le niveau de permission existe
    if permission_level not in PERMISSION_SETS:
        raise ValueError(f"Invalid permission level: {permission_level}")

    # Supprimer toutes les permissions existantes
    all_perms = set().union(*PERMISSION_SETS.values())
    app_label = Projects._meta.app_label
    for perm in all_perms:
        remove_perm(f"{app_label}.{perm}", user, project)

    # Assigner les nouvelles permissions
    for perm in PERMISSION_SETS[permission_level]:
        assign_perm(f"{app_label}.{perm}", user, project)

    return True


def revoke_project_permissions(user, project):
    """Révoquer toutes les permissions d'un utilisateur pour un projet."""
    if user.profile.odk_role in ADMIN_ROLES:
        return True

    all_perms = set().union(*PERMISSION_SETS.values())
    app_label = Projects._meta.app_label
    for perm in all_perms:
        remove_perm(f"{app_label}.{perm}", user, project)

    return True


def get_project_users_with_permissions(project):
    """Retourner tous les utilisateurs avec leurs permissions pour un projet."""
    users_with_perms = get_users_with_perms(
        project, attach_perms=True, with_group_users=False
    )
    return users_with_perms


def get_user_permission_level(user, project):
    """
    Déterminer le niveau de permission d'un utilisateur pour un projet.
    Retourne le niveau le plus élevé accordé.
    """
    if user.profile.odk_role in ADMIN_ROLES:
        return "manage"

    # Vérifier du niveau le plus élevé au plus bas
    for level in ["manage", "contribute", "submit", "read"]:
        perms = PERMISSION_SETS[level]
        app_label = Projects._meta.app_label
        if all(user.has_perm(f"{app_label}.{perm}", project) for perm in perms):
            return level

    return None
