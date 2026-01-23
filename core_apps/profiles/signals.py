import logging
from typing import Any, Type
from django.conf import settings
from django.db.models.base import Model
from django.db.models.signals import post_save
from django.dispatch import receiver
from core_apps.profiles.models import Profile
from core_apps.users.models import User

logger = logging.getLogger(__name__)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance: User, created: bool, **kwargs: Any) -> None:
    if created and instance.email != settings.ANONYMOUS_USER_NAME:
        Profile.objects.create(user=instance)
        logger.info(f"Profile created for {instance.first_name} {instance.last_name}")
    else:
        logger.info(
            f"Profile already exists for {instance.first_name} {instance.last_name}"
        )


# TODO: Remove Orphaned object permissions
# from django.contrib.contenttypes.models import ContentType
# from django.db.models import Q
# from django.db.models.signals import pre_delete
# from guardian.models import User
# from guardian.models import UserObjectPermission
# from guardian.models import GroupObjectPermission
#
#
# def remove_obj_perms_connected_with_user(sender, instance, **kwargs):
#     filters = Q(content_type=ContentType.objects.get_for_model(instance),
#                 object_pk=instance.pk)
#     UserObjectPermission.objects.filter(filters).delete()
#     GroupObjectPermission.objects.filter(filters).delete()
#
#
# pre_delete.connect(remove_obj_perms_connected_with_user, sender=User)
