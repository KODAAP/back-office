from logging import Logger

from django.db.models.signals import post_save
from django.dispatch import receiver

from core_apps.projects.models import Projects
from core_apps.projects.services import assign_project_permission

logger = Logger(__name__)


@receiver(post_save, sender=Projects)
def assign_creator_permissions(sender, instance, created, **kwargs):
    if created and instance.created_by:
        user = instance.created_by
        role = getattr(user.profile, "odk_role", None)

        # Determine the best level allowed for this user
        if role in ["administrator", "manager"]:
            level = "manage"
        elif role == "insuco_user":
            level = "contribute"
        else:
            level = "read"

        try:
            assign_project_permission(user, instance, level)
        except Exception as e:
            # Use logger.error instead of print to see the error in your logs
            logger.error(
                f"Error assigning {level} permissions to creator {user.email}: {e}"
            )
