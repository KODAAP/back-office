from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from core_apps.common.models import TimeStampedModel

User = get_user_model()


class ODKUserSessions(TimeStampedModel):
    odk_token = models.CharField(verbose_name="Odk Token")
    token_expired_at = models.DateTimeField(verbose_name="Odk Token Expired", null=True)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, verbose_name="Sycosur User"
    )
    actor_id = models.BigIntegerField(verbose_name="Odk Actor ID", null=True)

    class Meta:
        db_table = "odk_user_sessions"
        verbose_name = "User Session"
        verbose_name_plural = "User Sessions"

    def __str__(self) -> str:
        return f"{self.user.email} Session"

    def is_valid(self) -> bool:
        if self.token_expired_at is None:
            return False
        return self.token_expired_at > timezone.now()
