from django.db.models.signals import post_save
from django.dispatch import receiver

from core_apps.projects.models import Projects
from core_apps.projects.services import assign_project_permission


@receiver(post_save, sender=Projects)
def assign_creator_permissions(sender, instance, created, **kwargs):
    """
    Assigner automatiquement le niveau 'manage' au créateur du projet.
    """
    if created and instance.created_by:
        try:
            assign_project_permission(instance.created_by, instance, "manage")
        except Exception as e:
            print(f"Error assigning permissions to creator: {e}")
