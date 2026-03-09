from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.db.models.signals import pre_delete

from guardian.models import GroupObjectPermission, UserObjectPermission

User = get_user_model()


def remove_obj_perms_connected_with_user(sender, instance, **kwargs):
    """
    Signal receiver to delete object permissions associated with a user
    when the user instance is deleted. This prevents orphaned permissions.
    """
    filters = Q(
        content_type=ContentType.objects.get_for_model(instance), object_pk=instance.pk
    )
    UserObjectPermission.objects.filter(filters).delete()
    GroupObjectPermission.objects.filter(filters).delete()


pre_delete.connect(remove_obj_perms_connected_with_user, sender=User)
