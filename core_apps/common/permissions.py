from rest_framework import permissions

from .permissions_config import ADMIN_ROLES


class HasProjectPermission(permissions.BasePermission):
    """Permissions DRF pour Projects avec gestion fine objet et bypass rôles admin/manager."""

    # Mapping par méthode HTTP → permission par défaut
    method_map = {
        "GET": "projects.access_project",
        "HEAD": "projects.access_project",
        "OPTIONS": "projects.access_project",
        "PUT": "projects.manage_project",
        "PATCH": "projects.manage_project",
        "DELETE": "projects.manage_project",
    }

    def has_permission(self, request, view):
        # Bypass administrateur/manager si possible
        try:
            if (
                request.user.is_authenticated
                and request.user.profile.odk_role in ADMIN_ROLES
            ):
                return True
        except Exception:
            # profil manquant ou autre: pas de bypass
            return False

        if not request.user.is_authenticated:
            return False

        # Création (POST sur la collection): autoriser si l'utilisateur possède la
        # permission globale du modèle Django "projects.add_projects"
        if request.method == "POST":
            if request.user.profile.odk_role in ADMIN_ROLES:
                return True
            return request.user.has_perm("projects.add_projects")

        # if request.method =='DELETE':
        #     if request.user.profile.odk_role == ADMIN_ROLES.manager:
        #         return True
        #     return request.user.has_perm('projects.delete_project')

        return True

    def has_object_permission(self, request, view, obj):
        # Bypass administrateur/manager
        try:
            if request.user.profile.odk_role in ADMIN_ROLES:
                return True
        except Exception:
            return False

        # Perm requise spécifiée par la vue, sinon par la méthode HTTP
        required = getattr(view, "required_permission", None)
        if required is None:
            required = self.method_map.get(request.method)
        if not required:
            return False
        return request.user.has_perm(required, obj)


class HasFormPermission(HasProjectPermission):
    """Permissions pour les formulaires ODK, alignées avec les codenames du modèle."""

    method_map = {
        "GET": "projects.view_form",
        "POST": "projects.create_form",
        "PUT": "projects.edit_form",
        "PATCH": "projects.edit_form",
        "DELETE": "projects.delete_form",
    }


class HasSubmissionPermission(HasProjectPermission):
    """Permissions pour les soumissions ODK, alignées avec les codenames du modèle."""

    method_map = {
        "GET": "projects.view_submission",
        "POST": "projects.add_submission",
        "PUT": "projects.edit_submission",
        "PATCH": "projects.edit_submission",
        "DELETE": "projects.delete_submission",
    }

class CanChangeODKRole(permissions.BasePermission):
    # Only users with an administrative role can change another user ODK role
    def has_permission(self, request, view):
        try:
            return request.user.profile.odk_role in ADMIN_ROLES
        except AttributeError:
            return False