import logging

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from guardian.shortcuts import get_objects_for_user
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from core_apps.common.permissions import HasProjectPermission
from core_apps.common.permissions_config import ADMIN_ROLES
from core_apps.common.renderers import GenericJSONRenderer
from core_apps.common.tasks import send_email_task
from core_apps.common.utils import log_audit_action, truthy
from core_apps.profiles.models import Profile
from core_apps.projects.services import (
    assign_project_permission,
    can_assign_project_permissions,
    get_project_users_with_permissions,
    revoke_project_permissions,
)

from ..profiles.views import StandardResultsSetPagination
from .models import Projects
from .serializers import (
    AssignProjectPermissionSerializer,
    ProjectPermissionUserSerializer,
    ProjectSerializer,
)

User = get_user_model()


logger = logging.getLogger(__name__)


class ProjectListCreateView(generics.ListCreateAPIView):
    """
    View for listing and creating projects.
    GET: List all projects
    POST: Create a new project
    Query parameters for GET:
    - include_deleted: if true, include deleted projects in the results (default: false)
    - include_archived: if true, include archived projects in the results (default: false)
    """

    queryset = Projects.objects.filter(deleted=False, archived=False)
    serializer_class = ProjectSerializer
    renderer_classes = [GenericJSONRenderer]
    permission_classes = [HasProjectPermission]

    def get_queryset(self):
        """Return only projects the user can access, with optional deleted/archived inclusion."""
        user = self.request.user
        role = getattr(getattr(user, "profile", None), "odk_role", None)

        include_deleted = truthy(self.request.query_params.get("add_deleted"))
        include_archived = truthy(self.request.query_params.get("add_archived"))

        if role == Profile.ODKRole.ADMINISTRATOR:
            # Administrators see all projects by default
            qs = Projects.objects.all()
        else:
            # Restrict to projects the user has access to via object permissions
            qs = get_objects_for_user(user, "projects.access_project", klass=Projects)

        # Apply common filters
        if not include_deleted:
            qs = qs.filter(deleted=False)

        # For administrators, archived projects are included by default
        # (unless add_archived=false is explicitly provided)
        if role == Profile.ODKRole.ADMINISTRATOR:
            if (
                not include_archived
                and self.request.query_params.get("add_archived") is not None
            ):
                qs = qs.filter(archived=False)
        elif not include_archived:
            qs = qs.filter(archived=False)

        return qs

    @property
    def object_label(self):
        """
        Return different object labels based on the HTTP method:
        - 'projects' for GET (list) operations
        - 'project' for POST (create) operations
        """
        return "project" if self.request.method == "POST" else "projects"

    # def create(self, request, *args, **kwargs):
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     self.perform_create(serializer)
    #     return Response({"detail":"Project created"}, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        """Create a project; allow if user has global add_projects or is admin/manager."""
        user = self.request.user
        role = getattr(getattr(user, "profile", None), "odk_role", None)
        has_global_create = user.has_perm("projects.add_projects")
        if not has_global_create and role not in ["administrator"]:
            raise PermissionDenied("Not allowed to create projects")
        serializer.save(created_by=user)


class UserAssignableProjectsListView(APIView):
    """
    Vue pour lister les projets qui peuvent être assignés à un utilisateur spécifique.
    GET: Liste tous les projets actifs (non supprimés, non archivés) auxquels l'utilisateur n'est pas encore assigné.
    Le paramètre `user_id` doit être fourni dans l'URL ou en query param.
    """

    serializer_class = ProjectSerializer
    renderer_classes = [GenericJSONRenderer]
    object_label = "projects"

    @swagger_auto_schema(
        operation_description="Liste tous les projets actifs (non supprimés, non archivés) "
        "auxquels l'utilisateur n'est pas encore assigné.",
        responses={200: ProjectSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="ID de l'utilisateur cible (si non fourni dans l'URL)",
                type=openapi.TYPE_INTEGER,
            )
        ],
    )
    def get(self, request, user_id=None, *args, **kwargs):
        # Restriction aux administrateurs (ADMIN_ROLES)
        user = request.user
        role = getattr(getattr(user, "profile", None), "odk_role", None)
        if role not in ADMIN_ROLES:
            return Response(
                {"detail": "You do not have permission to access this resource."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Récupérer l'ID de l'utilisateur cible depuis l'URL ou les paramètres de requête
        target_user_id = user_id or request.query_params.get("user_id")

        if not target_user_id:
            return Response(
                {"detail": "The user identifier (user_id) is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target_user = get_user_model().objects.get(pkid=target_user_id)
        except get_user_model().DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # 1. Récupérer tous les projets actifs (non supprimés, non archivés)
        all_active_projects = Projects.objects.filter(deleted=False, archived=False)

        # 2. Identifier les projets auxquels l'utilisateur cible a déjà accès via guardian
        # On utilise 'access_project' comme permission de base pour l'assignation
        assigned_projects = get_objects_for_user(
            target_user, "projects.access_project", klass=Projects
        )

        # 3. Exclure les projets déjà assignés
        assignable_projects = all_active_projects.exclude(
            id__in=assigned_projects.values_list("id", flat=True)
        )

        # 4. Sérialiser et retourner la réponse
        serializer = self.serializer_class(
            assignable_projects,
            many=True,
            context={"request": request, "target_user": target_user},
        )
        return Response(serializer.data)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    View for retrieving, updating and deleting a project.
    GET: Retrieve a project
    PUT/PATCH: Update a project
    DELETE: Delete a project
    """

    queryset = Projects.objects.filter(deleted=False)
    serializer_class = ProjectSerializer
    lookup_field = "pkid"
    permission_classes = [HasProjectPermission]

    def get_renderers(self):
        if self.request.method in ["PUT", "PATCH", "GET"]:
            return [GenericJSONRenderer()]
        return super().get_renderers()

    @property
    def object_label(self):
        if self.request.method in ["PUT", "PATCH", "GET"]:
            return "project"
        raise AttributeError("object_label is not defined for this HTTP method")

    def perform_update(self, serializer):
        """Update the project"""
        project = serializer.save()
        return Response(project, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        """Soft delete the project by setting deleted=True"""
        instance.deleted = True
        instance.deleted_at = timezone.now()
        instance.save()


class ProjectArchiveView(APIView):
    permission_classes = [HasProjectPermission]
    required_permission = "projects.archive_project"

    def patch(self, request, pk, *args, **kwargs):
        try:
            project = Projects.objects.get(pkid=pk, deleted=False)
        except Projects.DoesNotExist:
            return Response(
                {"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Object-level permission check
        self.check_object_permissions(request, project)

        project.archived = True
        project.archived_at = timezone.now()
        project.save()

        return Response({"detail": "Project Archived"}, status=status.HTTP_200_OK)


class ProjectUnarchiveView(APIView):
    permission_classes = [HasProjectPermission]
    required_permission = "projects.archive_project"

    def patch(self, request, pk, *args, **kwargs):
        try:
            project = Projects.objects.get(pkid=pk, deleted=False, archived=True)
        except Projects.DoesNotExist:
            return Response(
                {"detail": "Project not found in archived projects."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Object-level permission check
        self.check_object_permissions(request, project)

        project.archived = False
        project.archived_at = None
        project.save()
        # Log unarchive action
        log_audit_action(
            user=request.user,
            action="unarchive",
            resource_type="project",
            resource_id=str(project.id),
            details={"message": "Project unarchived"},
            success=True,
            request=request,
        )

        return Response({"detail": "Project Unarchived"}, status=status.HTTP_200_OK)


class ProjectRestoreView(APIView):
    permission_classes = [HasProjectPermission]
    required_permission = "projects.restore_project"

    def patch(self, request, pk, *args, **kwargs):
        try:
            project = Projects.objects.get(pkid=pk, deleted=True)
        except Projects.DoesNotExist:
            return Response(
                {"detail": "Project not found in deleted projects."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Object-level permission check
        self.check_object_permissions(request, project)

        project.deleted = False
        project.deleted_at = None
        project.save()
        # Log restore action
        log_audit_action(
            user=request.user,
            action="restore",
            resource_type="project",
            resource_id=str(project.id),
            details={"message": "Project restored"},
            success=True,
            request=request,
        )
        return Response({"detail": "Project Restored"}, status=status.HTTP_200_OK)


# =====================================================================================
# ===============PROJECT PERMISSION MANAGEMENT========================================
# ====================================================================================


class ProjectPermissionAssignView(APIView):
    """
    Assigns a specific permission level for a project to a user.

    Handles POST requests to assign a permission (e.g., 'viewer', 'editor')
    to a specified user for a given project. The requesting user must have
    'manage_project' permissions on the project.
    """

    # TODO: verify if user has already the permission on the project, if so return the appropriate message
    permission_classes = [HasProjectPermission]
    required_permission = "projects.manage_project"

    @swagger_auto_schema(
        operation_description="Assigne un niveau de permission spécifique sur un projet à un utilisateur.",
        request_body=AssignProjectPermissionSerializer,
        responses={
            201: openapi.Response(
                description="Permission assignée avec succès",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "user": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "project": openapi.Schema(type=openapi.TYPE_STRING),
                        "permission_level": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: "Requête invalide ou erreur d'assignation",
            403: "Permission refusée",
        },
    )
    def post(self, request, pkid):
        project = get_object_or_404(Projects, pkid=pkid, deleted=False)

        # Object-level permission check via DRF permission class
        self.check_object_permissions(request, project)

        # Additional check: verify actor can assign permissions (object OR global manage_project)
        if not can_assign_project_permissions(request.user, project):
            raise PermissionDenied(
                "You do not have the right to assign permissions for this project"
            )

        serializer = AssignProjectPermissionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(pkid=serializer.validated_data["user_id"])
        if user.profile.odk_role == Profile.ODKRole.ADMINISTRATOR:
            raise PermissionDenied(
                "It is not possible to assign a project to an administrator."
            )
        level = serializer.validated_data["permission_level"]

        try:
            assign_project_permission(user, project, level)
            return Response(
                {
                    "user": user.pkid,
                    "project": project.name,
                    "permission_level": level,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProjectPermissionRevokeView(APIView):
    """
    Revokes all permissions for a specific user from a project.

    Handles DELETE requests to remove a user's access to a project.
    The requesting user must have 'manage_project' permissions on the project.
    """

    permission_classes = [HasProjectPermission]
    required_permission = "projects.manage_project"

    @swagger_auto_schema(
        operation_description="Révoque toutes les permissions d'un utilisateur spécifique pour un projet.",
        responses={
            204: "Permissions révoquées avec succès",
            403: "Impossible de révoquer les permissions d'un administrateur",
            404: "Projet ou utilisateur non trouvé",
        },
    )
    def delete(self, request, pkid, user_id):
        project = get_object_or_404(Projects, pkid=pkid, deleted=False)
        # Object-level permission check via DRF permission class
        self.check_object_permissions(request, project)

        user = get_object_or_404(User, pkid=user_id)
        # si user a odk_role = administrator, on ne peut pas le retirer de son projet
        if user.profile.odk_role == Profile.ODKRole.ADMINISTRATOR:
            raise PermissionDenied(
                "It is not possible to revoke a project from an administrator."
            )
        revoke_project_permissions(user, project)

        # Notify all administrators
        admin_emails = list(
            Profile.objects.filter(odk_role=Profile.ODKRole.ADMINISTRATOR)
            .select_related("user")
            .values_list("user__email", flat=True)
        )

        if admin_emails:
            context = {
                "user_full_name": user.get_full_name,
                "user_email": user.email,
                "project_name": project.name,
                "revoked_by": request.user.get_full_name,
                "timestamp": timezone.now(),
            }
            html_message = render_to_string(
                "emails/revocation_notification.html", context
            )
            send_email_task.delay(
                subject="Notification de révocation de permissions",
                message=f"Les permissions de {user.get_full_name} ont été révoquées pour le projet {project.name}.",
                recipient_list=admin_emails,
                html_message=html_message,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectPermissionListView(APIView):
    """
    Lists all users and their assigned permissions for a specific project.

    Handles GET requests to retrieve a list of users associated with a
    project and their respective permission levels. The requesting user must
    have at least 'access_project' permission on the project.
    """

    permission_classes = [HasProjectPermission]
    required_permission = "projects.access_project"

    @swagger_auto_schema(
        operation_description="Liste tous les utilisateurs et leurs permissions assignées pour un projet spécifique.",
        responses={200: ProjectPermissionUserSerializer(many=True)},
    )
    def get(self, request, pkid):
        project = get_object_or_404(Projects, pkid=pkid, deleted=False)

        # Object-level permission check via DRF permission class
        self.check_object_permissions(request, project)

        users_with_perms = get_project_users_with_permissions(project)

        # Serialize the user data.
        users_list = list(users_with_perms.keys())
        serializer = ProjectPermissionUserSerializer(
            users_list, many=True, context={"project": project}
        )

        return Response(
            {"status_code": status.HTTP_200_OK, "users": serializer.data},
            status=status.HTTP_200_OK,
        )


class UserProjectListView(generics.ListAPIView):
    """
    View for listing projects assigned to a specific user.
    Accessible only by administrators.
    """

    serializer_class = ProjectSerializer
    renderer_classes = [GenericJSONRenderer]
    permission_classes = [HasProjectPermission]

    def get_queryset(self):
        user_id = self.kwargs.get("user_id")
        target_user = get_object_or_404(User, pkid=user_id)
        # Get projects where the target user has 'access_project' permission
        qs = get_objects_for_user(
            target_user, "projects.access_project", klass=Projects
        )

        include_deleted = truthy(self.request.query_params.get("add_deleted"))
        include_archived = truthy(self.request.query_params.get("add_archived"))

        user = self.request.user
        role = getattr(getattr(user, "profile", None), "odk_role", None)

        # Apply common filters
        if not include_deleted:
            qs = qs.filter(deleted=False)

        if role == Profile.ODKRole.ADMINISTRATOR:
            # If the requester is an admin, show all projects of the target user
            # including archived ones by default
            if (
                not include_archived
                and self.request.query_params.get("add_archived") is not None
            ):
                qs = qs.filter(archived=False)
        elif not include_archived:
            qs = qs.filter(archived=False)

        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user_id = self.kwargs.get("user_id")
        target_user = get_object_or_404(User, pkid=user_id)
        context["target_user"] = target_user
        return context

    @property
    def object_label(self):
        return "userProjects"
