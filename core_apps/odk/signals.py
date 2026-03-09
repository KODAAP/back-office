from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from ..projects.models import Projects
from .cache import ODKCacheManager

User = get_user_model()


@receiver(post_save, sender=Projects)
def invalidate_project_cache(sender, instance, created, **kwargs):
    """Invalide le cache lorsqu'un projet est modifié"""
    # Invalide le cache pour tous les utilisateurs ayant une permission sur ce projet
    users_with_permission = User.objects.filter(
        userobjectpermission__content_type__model="projects",
        userobjectpermission__object_pk=instance.pk,
    ).distinct()

    for user in users_with_permission:
        ODKCacheManager.invalidate_project_cache(user.id, instance.odk_id)


# @receiver(post_save, sender=ODKForms)
# def invalidate_form_cache(sender, instance, created, **kwargs):
#     """Invalide le cache lorsqu'un formulaire est modifié"""
#     # Invalide le cache pour tous les utilisateurs ayant une permission sur le projet
#     users_with_permission = User.objects.filter(
#         odk_permissions__project=instance.project
#     ).distinct()
#
#     for user in users_with_permission:
#         ODKCacheManager.invalidate_project_cache(user.id, instance.project.odk_id)


# @receiver(post_save, sender=ProjectPermissions)
# def invalidate_permission_cache(sender, instance, created, **kwargs):
#     """Invalide le cache lorsqu'une permission est modifiée"""
#     # Invalide le cache pour l'utilisateur concerné
#     ODKCacheManager.invalidate_project_cache(instance.user.id, instance.project.odk_id)
#     ODKCacheManager.invalidate_user_cache(instance.user.id)


# @receiver(post_delete, sender=ProjectPermissions)
# def invalidate_permission_cache_on_delete(sender, instance, **kwargs):
#     """Invalide le cache lorsqu'une permission est supprimée"""
#     # Invalide le cache pour l'utilisateur concerné
#     ODKCacheManager.invalidate_project_cache(instance.user.id, instance.project.odk_id)
#     ODKCacheManager.invalidate_user_cache(instance.user.id)
