from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from guardian.shortcuts import assign_perm, remove_perm

from core_apps.common.permissions_config import PERMISSION_SETS
from core_apps.projects.models import Projects
from core_apps.projects.services import assign_project_permission

User = get_user_model()


class Command(BaseCommand):
    help = "Assign permissions to a user for a project or assign global permissions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-email", type=str, help="Email of the user", required=True
        )

        # Mutually exclusive group: either project-based or global permission
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--project-id",
            type=int,
            help="ID (pkid) of the project (for project-level permissions)",
        )
        group.add_argument(
            "--global-perm",
            type=str,
            help="Global permission to assign (format: app_label.codename, e.g., projects.add_projects)",
        )

        parser.add_argument(
            "--level",
            type=str,
            choices=list(PERMISSION_SETS.keys()),
            help="Permission level (required with --project-id, one of: read, submit, contribute, manage)",
        )
        parser.add_argument(
            "--remove",
            action="store_true",
            help="Remove the permission instead of assigning it (only with --global-perm)",
        )

    def handle(self, *args, **options):
        user_email = options["user_email"]
        global_perm = options.get("global_perm")
        project_id = options.get("project_id")
        level = options.get("level")
        remove = options.get("remove", False)

        # Get user
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {user_email} not found"))
            return

        # Mode 1: Global permission
        if global_perm:
            if remove:
                remove_perm(global_perm, user)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Removed global permission {global_perm} from {user_email}"
                    )
                )
            else:
                assign_perm(global_perm, user)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Assigned global permission {global_perm} to {user_email}"
                    )
                )
            return

        # Mode 2: Project-level permission
        if not level:
            self.stdout.write(
                self.style.ERROR("--level is required when using --project-id")
            )
            return

        try:
            project = Projects.objects.get(pkid=project_id)
        except Projects.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Project {project_id} not found"))
            return

        try:
            assign_project_permission(user, project, level)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully assigned {level} permission to {user_email} for project {project.name}"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
