import logging
from typing import Any

from django.conf import settings
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
